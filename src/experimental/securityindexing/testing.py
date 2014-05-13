import contextlib
import string

import plone.app.testing as pa_testing
from plone.app.contenttypes.testing import (
    PLONE_APP_CONTENTTYPES_FIXTURE,
)
from plone.app.event.testing import PAEvent_FIXTURE
from Products.CMFCore.CMFCatalogAware import CMFCatalogAware
from plone.testing import z2
from plone import api


@contextlib.contextmanager
def catalog_disabled():
    catalog_tool = CMFCatalogAware._getCatalogTool
    CMFCatalogAware._getCatalogTool = lambda content_item: None
    yield
    CMFCatalogAware._getCatalogTool = catalog_tool


def _make_folder(id_, parent):
    return api.content.create(type='Folder',
                              container=parent,
                              id=id_)


def create_content_tree(parent, nwide, ndeep, level=0, verbose=False):
    count = 0
    if ndeep == 0:
        return count
    ndeep -= 1
    siblings = []
    for i in range(nwide):
        fid = string.ascii_lowercase[i]
        f = _make_folder(fid, parent=parent)
        siblings.append(f)
        count += 1
    if verbose:
        print('/'.join(f.getPhysicalPath()[:-1]))
        print(' ' * level, ', '.join(s.getId() for s in siblings))
    level += 1
    for sibling in siblings:
        count += create_content_tree(sibling, nwide, ndeep, level=level, verbose=verbose)
    return count
        

class BenchmarkLayer(pa_testing.PloneSandboxLayer):

    n_wide = 5
    n_deep = 5

    def _install_packages(self, portal):
        pass

    def _uninstall_packages(self, portal):
        # TODO: subclass should remove our package cleanly....
        pass

    def _sanity_checks(self):
        raise NotImplementedError()
       
    def setUpPloneSite(self, portal):
        super(BenchmarkLayer, self).setUpPloneSite(portal)
        pa_testing.setRoles(portal, pa_testing.TEST_USER_ID, ['Manager'])
        pa_testing.login(portal, pa_testing.TEST_USER_NAME)
        self._install_packages(portal)
        self.top = api.content.create(api.portal.get(), id='bench-root', type='Folder')
        with catalog_disabled():
            create_content_tree(self.top, self.n_wide, self.n_deep)
        catalog = api.portal.get_tool('portal_catalog')
        catalog.clearFindAndRebuild()
        self._sanity_checks()

    def tearDownPloneSite(self, portal):
        self._uninstall_packages(portal)
        super(BenchmarkLayer, self).tearDownPloneSite(portal)

       
class VanillaDXBenchLayer(BenchmarkLayer):

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE, 
                    PAEvent_FIXTURE, 
                    pa_testing.PLONE_FIXTURE)

    def _sanity_checks(self):
        assert self.top.meta_type.startswith('Dexterity')


class InstalledDXBenchLayer(VanillaDXBenchLayer):

    def _install_packages(self, portal):
        self.applyProfile(portal, 'experimental.securityindexing:default')

    def setUpZope(self, app, configuration_context): 
        setup_zope = super(InstalledDXBenchLayer, self).setUpZope
        setup_zope(app, configuration_context)
        import experimental.securityindexing
        self.loadZCML(package=experimental.securityindexing,
                      context=configuration_context)


class VanillaATBenchLayer(BenchmarkLayer):

    def _sanity_checks(self):
        assert self.top.meta_type.startswith('ATFolder')


class InstalledATBenchLayer(VanillaATBenchLayer):

    def _install_packages(self, portal):
        self.applyProfile(portal, 'experimental.securityindexing:default')

    def setUpZope(self, app, configuration_context): 
        setup_zope = super(InstalledATBenchLayer, self).setUpZope
        setup_zope(app, configuration_context)
        import experimental.securityindexing
        self.loadZCML(package=experimental.securityindexing,
                      context=configuration_context)

        
class SecurityIndexingLayer(pa_testing.PloneSandboxLayer):

    defaultBases = (pa_testing.PLONE_FIXTURE,)

    def setUpZope(self, app, configuration_context):
        # Load ZCML
        import experimental.securityindexing
        self.loadZCML(package=experimental.securityindexing,
                      context=configuration_context)

    def setUpPloneSite(self, portal):
        self.applyProfile(portal, 'experimental.securityindexing:default')

    def tearDownZope(self, app):
        z2.uninstallProduct(app, 'experimental.securityindexing')


FIXTURE = SecurityIndexingLayer()

INTEGRATION = pa_testing.IntegrationTesting(
    bases=(FIXTURE,),
    name='SecurityIndexingLayer:Integration'
)

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
