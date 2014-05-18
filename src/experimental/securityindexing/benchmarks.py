"""Abuse zope.testrunner layers for the purpose of generating benchmarks.

Here we attempt to do some rudimentary testing against
Plone sites setup with Archetypes (AT) and Dexterity (DX)
via plone.app.contenttypes.

Layers are configured thus:
  - Without the optimisation's ('Vanilla')
  - With the optimisation addon ('Installed')

The same 'tests' are run for the Vanilla and Installed variants.

"""
from __future__ import print_function
import collections
import contextlib
import csv
import cProfile
import datetime
import functools
import os
import unittest
import string
import time

from Products.CMFCore.CMFCatalogAware import CMFCatalogAware
from plone import api
from plone.app.contenttypes.testing import (
    PLONE_APP_CONTENTTYPES_FIXTURE,
)
import plone.app.testing as pa_testing
import transaction

from . import testing


@contextlib.contextmanager
def timings():
    start = time.time()
    data = dict(elapsed=0)
    yield data
    data[b'duration'] = time.time() - start


def profile(func):
    @functools.wraps(func)
    def _do_profile(*args, **kw):
        prof = cProfile.Profile()
        try:
            prof.enable()
            result = func(*args, **kw)
        finally:
            prof.disable()
            path = b'/tmp/%s-%s-%s' % (
                func.__module__,
                func.__name__, os.getpid()
            )
            prof.dump_stats(path)
        return result
    return _do_profile


@contextlib.contextmanager
def catalog_disabled():
    catalog_tool = CMFCatalogAware._getCatalogTool
    CMFCatalogAware._getCatalogTool = lambda content_item: None
    yield
    CMFCatalogAware._getCatalogTool = catalog_tool


def create_content_tree(parent, nwide, ndeep,
                        commit_interval=500,
                        level=0, verbose=False):
    """Recursively create a tree of content.

    :param parent: The parent node.
    :type parent: IContentish
    :param nwide: The number of folders to create at each level.
    :type nwide: int
    :param ndeep: The number of levels deep the tree should be.
    :type ndeep: int
    :param level: The current level
    :type level: int
    :param verbose: Whether or not print each time a folder is created.
    :type verbose: bool
    """
    count = 0
    if ndeep == 0:
        return count
    ndeep -= 1
    siblings = []
    for i in range(nwide):
        fid = string.ascii_lowercase[i]
        folder = api.content.create(container=parent,
                                    type=b'Folder',
                                    id=fid)
        siblings.append(folder)
        count += 1
    if verbose:
        print(b'/'.join(folder.getPhysicalPath()[:-1]))
        print(b' ' * level, b', '.join(s.getId() for s in siblings))
    level += 1
    for sibling in siblings:
        count += create_content_tree(sibling, nwide, ndeep,
                                     commit_interval,
                                     level=level,
                                     verbose=verbose)
        if count % commit_interval == 0:
            transaction.savepoint()
    return count


class BenchmarkLayerMixin(object):
    """Mixin class for benchmark layers.

    Ensures that a tree of content is created after installation
    of packages is performed.
    """
    n_siblings = int(os.environ.get(b'BENCHMARK_N_SIBLINGS', 2))
    n_levels = int(os.environ.get(b'BENCHMARK_N_LEVELS', 2))

    def _sanity_checks(self):
        raise NotImplementedError()

    def setUpPloneSite(self, portal):
        pa_testing.setRoles(portal, pa_testing.TEST_USER_ID, [b'Manager'])
        pa_testing.login(portal, pa_testing.TEST_USER_NAME)
        wftool = api.portal.get_tool(b'portal_workflow')
        wftool.setDefaultChain(b'simple_publication_workflow')
        self.top = api.content.create(api.portal.get(),
                                      id=b'bench-root',
                                      type=b'Folder')
        with catalog_disabled():
            create_content_tree(self.top, self.n_siblings, self.n_levels)
        catalog = api.portal.get_tool(b'portal_catalog')
        catalog.clearFindAndRebuild()
        self._sanity_checks()


class BenchmarkATLayer(BenchmarkLayerMixin, pa_testing.PloneSandboxLayer):
    """A Plone 4.3.x layer for benchmarking.

    This layer installs no additional addons.
    """

    defaultBases = (pa_testing.PLONE_FIXTURE,)

    def _sanity_checks(self):
        assert self.top.meta_type.startswith(b'ATFolder')


class BenchmarkDXLayer(BenchmarkLayerMixin, pa_testing.PloneSandboxLayer):
    """A layer which ensure Dexteity is used for the default content."""

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,)

    def _sanity_checks(self):
        assert self.top.meta_type.startswith(b'Dexterity')


AT_FIXTURE = BenchmarkATLayer()

DX_FIXTURE = BenchmarkDXLayer()

# [A-Z]{3,3} Prefixing of layer names here
# is done to force ordering of layer executation
# by zope.testrunner, such that p.a.testing does not choke.
# For some reason DemoStorage created by p.testing.z2 goes AWOL
# unless DX tests run first. (p.a.event testing problem?)

VANILLA_AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_FIXTURE,),
    name=b'KKK_VanillaAT:Integration'
)
VANILLA_DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_FIXTURE,),
    name=b'JJJ_VanillaDX:Integration'
)
INSTALLED_AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_FIXTURE, testing.AT_FIXTURE),
    name=b'ZZZ_InstalledAT:Integration'
)
INSTALLED_DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_FIXTURE, testing.DX_FIXTURE),
    name=b'YYY_InstalledDX:Integration'
)


class BenchTestMixin(object):

    def _write_result(self, duration):
        pc = api.portal.get_tool(b'portal_catalog')
        portal = self.layer[b'portal']
        bench_root_path = b'/'.join(portal[b'bench-root'].getPhysicalPath())
        brains = pc.searchResults(path=bench_root_path)
        n_objects = len(brains)
        items = [
            (b'timestamp', datetime.datetime.now().isoformat()),
            (b'test-name', self.id()),
            (b'duration', duration),
            (b'n-objects', n_objects)
        ]
        row = collections.OrderedDict(items)
        results_path = os.environ.get(b'BENCHMARK_RESULTS_FILE',
                                      b'bench-results.csv')
        write_header = not os.path.exists(results_path)
        with open(results_path, b'a') as fp:
            writer = csv.DictWriter(fp, fieldnames=list(row))
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    def _call_mut(self, obj, *args, **kw):
        with timings() as timing_data:
            obj.reindexObjectSecurity()
        return timing_data[b'duration']

    def _get_obj(self, path=b''):
        return api.content.get(b'/plone/bench-root' + path)

    def test_reindexObjectSecurity_from_root_nochange(self):
        subject = self._get_obj()
        duration = self._call_mut(subject)
        self._write_result(duration)

    def test_reindexObjectSecurity_from_root_wfchange(self):
        subject = self._get_obj()
        api.content.transition(subject, b'publish')
        duration = self._call_mut(subject)
        self._write_result(duration)

    def test_reindexObjectSecurity_from_root_lrchange(self):
        subject = self._get_obj()
        api.user.create(username=b'bob',
                        email=b'bob@example.com')
        api.user.grant_roles(username=b'bob',
                             obj=subject,
                             roles=[b'Reader'])
        duration = self._call_mut(subject)
        self._write_result(duration)

    def test_reindexObjectSecurity_from_root_lrchange_with_lrblock(self):
        subject = self._get_obj()
        api.user.create(username=b'bob',
                        email=b'bob@example.com')
        api.user.grant_roles(username=b'bob',
                             obj=subject,
                             roles=[b'Reader'])
        blocked = subject[b'a']
        blocked.__ac_local_roles_block__ = True
        self._call_mut(blocked)
        duration = self._call_mut(subject)
        self._write_result(duration)


class VanillaATBenchmarks(BenchTestMixin, unittest.TestCase):

    layer = VANILLA_AT_INTEGRATION


class VanillaDXBenchmarks(BenchTestMixin, unittest.TestCase):

    layer = VANILLA_DX_INTEGRATION


class InstalledATBenchmarks(VanillaATBenchmarks):

    layer = INSTALLED_AT_INTEGRATION


class InstalledDXBenchmarks(VanillaDXBenchmarks):

    layer = INSTALLED_DX_INTEGRATION
