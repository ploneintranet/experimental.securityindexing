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
import cProfile
import datetime
import functools
import json
import logging
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

from experimental.securityindexing import testing


N_SIBLINGS = int(os.environ.get(b'BENCHMARK_N_SIBLINGS', 2))

N_LEVELS = int(os.environ.get(b'BENCHMARK_N_LEVELS', 2))

logger = logging.getLogger(testing.__package__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)


class Timings(object):

    def __init__(self, method):
        self._method = method
        self._duration = None
        self._test_ident = None
        self._test_ident_lbl_mapping = None
        self._results_path = os.environ.get(b'BENCHMARK_RESULTS_FILE',
                                            b'bench-results.json')
        assert os.access(os.path.dirname(self._results_path),
                         os.R_OK | os.W_OK)

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if any((exc_type, exc_value, tb)):
            return None
        self._write_result()

    def __call__(self, *args, **kw):
        start = time.time()
        rv = self._method(*args, **kw)
        self._duration = time.time() - start
        return rv

    def _write_result(self):
        timestamp = datetime.datetime.now().isoformat()
        pc = api.portal.get_tool(b'portal_catalog')
        bench_root_path = b'/'.join(self.context.getPhysicalPath())
        brains = pc.searchResults(path=bench_root_path)
        n_objects = len(brains)
        qi_tool = api.portal.get_tool(b'portal_quickinstaller')
        pkg_name = b'experimental.securityindexing'
        is_installed = qi_tool.isProductInstalled(pkg_name)
        classifier_fmt = b'{.content_type_identifier} {suffix}'
        suffix = b'Installed' if is_installed else b'Original'
        classifier = classifier_fmt.format(self, suffix=suffix)
        storage = collections.defaultdict(dict)
        try:
            with open(self._results_path, b'r') as fp:
                storage.update(json.load(fp))
        except (IOError, OSError, ValueError, TypeError) as err:
            print(err)
        bm_key_fmt = b'[N_SIBLINGS={n_siblings},N_LEVELS={n_levels}]'
        bm_key = bm_key_fmt.format(n_siblings=N_SIBLINGS, n_levels=N_LEVELS)
        bm_container = storage.setdefault(bm_key, {
            b'n_objects': n_objects,
            b'operation': b'Reindex Object Security',
            b'timestamp': timestamp
        })
        bm_settings = bm_container.setdefault(b'settings', {})
        lbls = bm_settings.setdefault(b'action-labels', {})
        lbls.update(self._test_ident_lbl_mapping)
        bm_results = bm_container.setdefault(b'results', {})
        classified = bm_results.setdefault(classifier, {})
        durations_by_action = classified.setdefault(b'action-duration', {})
        durations_by_action[self._test_ident] = self._duration
        with open(self._results_path, b'w') as fp:
            json.dump(storage, fp)

    @property
    def content_type_identifier(self):
        if self.context.meta_type.startswith(b'Dexterity'):
            return b'Dexterity'
        return b'Archetypes'

    def set_test_identifier_label_map(self, label_mapping):
        self._test_ident_lbl_mapping = collections.OrderedDict(label_mapping)

    def set_context(self, content_obj, test_identifier):
        self.context = content_obj
        self._test_ident = test_identifier


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


def create_content_tree(parent, n_siblings, n_levels,
                        commit_interval=500,
                        level=0, verbose=False):
    """Recursively create a tree of content.

    :param parent: The parent node.
    :type parent: IContentish
    :param n_siblings: The number of folders to create at each level.
    :type n_siblings: int
    :param n_levels: The number of levels deep the tree should be.
    :type n_levels: int
    :param level: The current level
    :type level: int
    :param verbose: Whether or not print each time a folder is created.
    :type verbose: bool
    """
    count = 0
    if n_levels == 0:
        return count
    n_levels -= 1
    siblings = []
    for i in range(n_siblings):
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
        count += create_content_tree(sibling,
                                     n_siblings,
                                     n_levels,
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
            create_content_tree(self.top, N_SIBLINGS, N_LEVELS)
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

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,
                    pa_testing.PLONE_FIXTURE)

    def _sanity_checks(self):
        assert self.top.meta_type.startswith(b'Dexterity')

    def setUpPloneSite(self, portal):
        # Delete a fodler created by the p.a{contenttypes,event} fixtures
        api.content.delete(obj=portal['robot-test-folder'])
        super(BenchmarkDXLayer, self).setUpPloneSite(portal)


VANILLA_AT_FIXTURE = BenchmarkATLayer()

INSTALLED_AT_FIXTURE = testing.SecurityIndexingLayer(
    bases=(VANILLA_AT_FIXTURE,),
    name=b'SecurityIndexingLayerAT:Integration'
)

VANILLA_DX_FIXTURE = BenchmarkDXLayer()

INSTALLED_DX_FIXTURE = testing.SecurityIndexingLayer(
    bases=(VANILLA_DX_FIXTURE,),
    name=b'SecurityIndexingLayerDX:Integration'
)

# [A-Z]{3,3} Prefixing of layer names here
# is done to force ordering of layer executation
# by zope.testrunner, such that p.a.testing does not choke.
# For some reason DemoStorage created by p.testing.z2 goes AWOL
# unless DX tests run first. (p.a.event testing problem?)

VANILLA_AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(VANILLA_AT_FIXTURE,),
    name=b'KKK_VanillaAT:Integration'
)

VANILLA_DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(VANILLA_DX_FIXTURE,),
    name=b'JJJ_VanillaDX:Integration'
)

INSTALLED_AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(INSTALLED_AT_FIXTURE,),
    name=b'ZZZ_InstalledAT:Integration'
)

INSTALLED_DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(INSTALLED_DX_FIXTURE,),
    name=b'YYY_InstalledDX:Integration'
)


class BenchTestMixin(object):

    def _call_mut(self, obj, test_identifier, *args, **kw):
        portal = api.portal.get()
        with Timings(obj.reindexObjectSecurity) as benchmark:
            benchmark.set_test_identifier_label_map([
                (u'lrchange', u'Local role change'),
                (u'lrchange_with_lrblock', u'Local role change with block'),
                (u'wfchange', u'Workflow state change'),
                (u'nochange', u'No change')
            ])
            benchmark.set_context(portal[b'bench-root'], test_identifier)
            benchmark()

    def _get_obj(self, path=b''):
        return api.content.get(b'/plone/bench-root' + path)

    def test_reindexObjectSecurity_from_root_nochange(self):
        subject = self._get_obj()
        self._call_mut(subject, 'nochange')

    def test_reindexObjectSecurity_from_root_wfchange(self):
        subject = self._get_obj()
        api.content.transition(subject, b'publish')
        self._call_mut(subject, 'wfchange')

    def test_reindexObjectSecurity_from_root_lrchange(self):
        subject = self._get_obj()
        api.user.create(username=b'bob',
                        email=b'bob@example.com')
        api.user.grant_roles(username=b'bob',
                             obj=subject,
                             roles=[b'Reader'])
        self._call_mut(subject, 'lrchange')

    def test_reindexObjectSecurity_from_root_lrchange_with_lrblock(self):
        subject = self._get_obj()
        api.user.create(username=b'bob',
                        email=b'bob@example.com')
        api.user.grant_roles(username=b'bob',
                             obj=subject,
                             roles=[b'Reader'])
        blocked = subject[b'a']
        blocked.__ac_local_roles_block__ = True
        blocked.reindexObjectSecurity()
        self._call_mut(subject, 'lrchange_with_lrblock')


class VanillaATBenchmarks(BenchTestMixin, unittest.TestCase):

    layer = VANILLA_AT_INTEGRATION


class VanillaDXBenchmarks(BenchTestMixin, unittest.TestCase):

    layer = VANILLA_DX_INTEGRATION


class InstalledATBenchmarks(VanillaATBenchmarks):

    layer = INSTALLED_AT_INTEGRATION


class InstalledDXBenchmarks(VanillaDXBenchmarks):

    layer = INSTALLED_DX_INTEGRATION
