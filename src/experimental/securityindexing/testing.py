from __future__ import print_function
import contextlib
import functools
import string
import time
import unittest

from plone import api
from plone.app.contenttypes.testing import (
    PLONE_APP_CONTENTTYPES_FIXTURE,
)
from plone.app.event.testing import PAEvent_FIXTURE
from Products.CMFCore.CMFCatalogAware import CMFCatalogAware
import plone.app.testing as pa_testing


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


@contextlib.contextmanager
def catalog_disabled():
    catalog_tool = CMFCatalogAware._getCatalogTool
    CMFCatalogAware._getCatalogTool = lambda content_item: None
    yield
    CMFCatalogAware._getCatalogTool = catalog_tool


def create_content_tree(parent, nwide, ndeep, 
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
        siblings.append(folder)
        count += 1
    if verbose:
        print('/'.join(f.getPhysicalPath()[:-1]))
        print(' ' * level, ', '.join(s.getId() for s in siblings))
    level += 1
    for sibling in siblings:
        count += create_content_tree(sibling, nwide, ndeep, 
                                     level=level, verbose=verbose)
    return count
        

class SecurityIndexingLayerMixin(object):
    """Mixin for layers."""

    def setUpZope(self, app, configuration_context):
        super(SecurityIndexingLayerMixin, self).setUpZope(
            app, 
            configuration_context
        )
        # Load ZCML
        import experimental.securityindexing
        self.loadZCML(package=experimental.securityindexing,
                      context=configuration_context)

    def setUpPloneSite(self, portal):
        super(SecurityIndexingLayerMixin, self).setUpPloneSite(portal)
        self.applyProfile(portal, 'experimental.securityindexing:default')


class BenchmarkLayer(pa_testing.PloneSandboxLayer):
    """Base class for benchmark layers.

    Ensures that a tree of content is created after installation
    of packages is performed.
    """
    n_wide = 2
    n_deep = 2

    def _sanity_checks(self):
        raise NotImplementedError()
       
    def setUpPloneSite(self, portal):
        pa_testing.setRoles(portal, pa_testing.TEST_USER_ID, ['Manager'])
        pa_testing.login(portal, pa_testing.TEST_USER_NAME)
        super(BenchmarkLayer, self).setUpPloneSite(portal)
        self.top = api.content.create(api.portal.get(), id='bench-root', type='Folder')
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


class InstalledDXBenchLayer(SecurityIndexingLayerMixin, VanillaDXBenchLayer):
    """A benchmark layer that installs plone.app.contenttypes,
    and this addon package.
    """


class VanillaATBenchLayer(BenchmarkLayer):
    """A Plone 4.3.x layer for benchmarking.

    This layer installs no additional addons.
    """

    def _sanity_checks(self):
        assert self.top.meta_type.startswith('ATFolder')


class InstalledATBenchLayer(SecurityIndexingLayerMixin, VanillaATBenchLayer):
    """A benchmark layer this addon package installed."""


DX_VANILLA_FIXTURE = VanillaDXBenchLayer()
DX_VANILLA_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_VANILLA_FIXTURE,),
    name='VanillaDXLayer:Integration'
)

DX_INSTALLED_FIXTURE = InstalledDXBenchLayer()
DX_INSTALLED_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_INSTALLED_FIXTURE,),
    name='InstalledDXLayer:Integration'
)

AT_VANILLA_FIXTURE = VanillaATBenchLayer()
AT_VANILLA_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_VANILLA_FIXTURE,),
    name='VanillaATLayer:Integration'
)

AT_INSTALLED_FIXTURE = InstalledATBenchLayer()
AT_INSTALLED_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_INSTALLED_FIXTURE,),
    name='InstalledATLayer:Integration'
)



