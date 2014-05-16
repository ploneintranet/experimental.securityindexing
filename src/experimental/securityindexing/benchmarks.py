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
from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.event.testing import PAEvent_FIXTURE
import pkg_resources
import plone.app.testing as pa_testing
import transaction

from . import testing


def timed(func):
    @functools.wraps(func)
    def timer(*args, **kw):
        start = time.time()
        elapsed = 0
        try:
            func(*args, **kw)
        finally:
            elapsed = time.time() - start
        return elapsed
    return timer


def profile(func):
    @functools.wraps(func)
    def _do_profile(*args, **kw):
        prof = cProfile.Profile()
        try:
            prof.enable()
            result = func(*args, **kw)
        finally:
            prof.disable()
            path = '/tmp/%s-%s-%s' % (
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
                        total=0,
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
                                    type='Folder',
                                    id=fid)
        total += 1
        siblings.append(folder)
        count += 1
    if verbose:
        print('/'.join(folder.getPhysicalPath()[:-1]))
        print(' ' * level, ', '.join(s.getId() for s in siblings))
    level += 1
    for sibling in siblings:
        count += create_content_tree(sibling, nwide, ndeep,
                                     commit_interval,
                                     total=total,
                                     level=level,
                                     verbose=verbose)
        if total % commit_interval == 0:
            transaction.commit()
    return count


class BenchmarkLayer(pa_testing.PloneSandboxLayer):
    """Base class for benchmark layers.

    Ensures that a tree of content is created after installation
    of packages is performed.
    """
    n_wide = 7
    n_deep = 5

    def _sanity_checks(self):
        raise NotImplementedError()

    def setUpPloneSite(self, portal):
        pa_testing.setRoles(portal, pa_testing.TEST_USER_ID, ['Manager'])
        pa_testing.login(portal, pa_testing.TEST_USER_NAME)
        super(BenchmarkLayer, self).setUpPloneSite(portal)
        wftool = api.portal.get_tool('portal_workflow')
        wftool.setDefaultChain('simple_publication_workflow')
        self.top = api.content.create(api.portal.get(),
                                      id='bench-root',
                                      type='Folder')
        with catalog_disabled():
            create_content_tree(self.top, self.n_wide, self.n_deep)
        catalog = api.portal.get_tool('portal_catalog')
        catalog.clearFindAndRebuild()
        self._sanity_checks()


class VanillaDXBenchLayer(BenchmarkLayer):
    """A layer which ensure Dexteity is used for the default content types."""

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,
                    PAEvent_FIXTURE,
                    pa_testing.PLONE_FIXTURE)

    def _sanity_checks(self):
        assert self.top.meta_type.startswith('Dexterity')


class InstalledDXBenchLayer(testing.SecurityIndexingLayerMixin,
                            VanillaDXBenchLayer):
    """A benchmark layer that installs plone.app.contenttypes,
    and this addon package.
    """


class VanillaATBenchLayer(BenchmarkLayer):
    """A Plone 4.3.x layer for benchmarking.

    This layer installs no additional addons.
    """

    defaultBases = (pa_testing.PLONE_FIXTURE,)

    def _sanity_checks(self):
        assert self.top.meta_type.startswith('ATFolder')


class InstalledATBenchLayer(testing.SecurityIndexingLayerMixin,
                            VanillaATBenchLayer):
    """A benchmark layer this addon package installed."""


DX_VANILLA_FIXTURE = VanillaDXBenchLayer()
DX_VANILLA_INTEGRATION = pa_testing.FunctionalTesting(
    bases=(DX_VANILLA_FIXTURE,),
    name='VanillaDXLayer:Functional'
)

DX_INSTALLED_FIXTURE = InstalledDXBenchLayer()
DX_INSTALLED_INTEGRATION = pa_testing.FunctionalTesting(
    bases=(DX_INSTALLED_FIXTURE,),
    name='InstalledDXLayer:Functional'
)

AT_VANILLA_FIXTURE = VanillaATBenchLayer()
AT_VANILLA_INTEGRATION = pa_testing.FunctionalTesting(
    bases=(AT_VANILLA_FIXTURE,),
    name='VanillaATLayer:Functional'
)

AT_INSTALLED_FIXTURE = InstalledATBenchLayer()
AT_INSTALLED_INTEGRATION = pa_testing.FunctionalTesting(
    bases=(AT_INSTALLED_FIXTURE,),
    name='InstalledATLayer:Functional'
)


class BenchTestMixin(object):

    results_path = pkg_resources.resource_filename(
        __package__, 'bench-results.csv'
    )

    def _write_result(self, duration):
        pc = api.portal.get_tool('portal_catalog')
        portal = self.layer['portal']
        bench_root_path = '/'.join(portal['bench-root'].getPhysicalPath())
        brains = pc.searchResults(path=bench_root_path)
        n_objects = len(brains)
        items = [
            ('timestamp', datetime.datetime.now().isoformat()),
            ('test-name', self.id()),
            ('duration', duration),
            ('n-objects', n_objects)
        ]
        row = collections.OrderedDict(items)
        with open(self.results_path, 'a') as fp:
            writer = csv.DictWriter(fp, list(row))
            writer.writerow(row)
        print(row)

    def _call_mut(self, obj, *args, **kw):
        method = timed(obj.reindexObjectSecurity)
        return method(*args, **kw)

    def _get_obj(self, path=''):
        return api.content.get('/plone/bench-root' + path)

    def test_reindexObjectSecurity_from_root_nochange(self):
        subject = self._get_obj()
        duration = self._call_mut(subject)
        self._write_result(duration)

    def test_reindexObjectSecurity_from_root_wfchange(self):
        subject = self._get_obj()
        api.content.transition(subject, 'publish')
        duration = self._call_mut(subject)
        self._write_result(duration)

    def test_reindexObjectSecurity_from_root_lrchange(self):
        subject = self._get_obj()
        api.user.create(username='bob',
                        email='bob@example.com')
        api.user.grant_roles(username='bob',
                             obj=subject,
                             roles=['Reader'])
        duration = self._call_mut(subject)
        self._write_result(duration)

    def test_reindexObjectSecurity_from_root_lrchange_with_lrblock(self):
        subject = self._get_obj()
        api.user.create(username='bob',
                        email='bob@example.com')
        api.user.grant_roles(username='bob',
                             obj=subject,
                             roles=['Reader'])
        blocked = subject['a']
        blocked.__ac_local_roles_block__ = True
        self._call_mut(blocked)
        duration = self._call_mut(subject)
        self._write_result(duration)


class VanillaDXBenchTest(BenchTestMixin, unittest.TestCase):

    layer = DX_VANILLA_INTEGRATION


class InstalledDXBenchTest(VanillaDXBenchTest):

    layer = DX_INSTALLED_INTEGRATION


class VanillaATBenchTest(BenchTestMixin, unittest.TestCase):

    layer = AT_VANILLA_INTEGRATION


class InstalledATBenchTest(VanillaATBenchTest):

    layer = AT_INSTALLED_INTEGRATION


if __name__ == '__main__':
    unittest.main()
