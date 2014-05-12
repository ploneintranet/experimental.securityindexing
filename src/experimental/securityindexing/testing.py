from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting

from plone.testing import z2

class BenchmarkLayer(PloneSandboxLayer):

    n_wide = NotImplemented
    n_deep = NotImplemented

    def create_content_tree(self, parent=None):
        parent = parent or self['portal']
        for idx in self.n_wide:
            for idx2 in self.n_deep:
                folder = api.content.create(container=parent,
                                            type='Folder',
                                            id='folder-%d' % idx)
            self.create_content_tree(parent=folder)
                             
        
class SecurityIndexingLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import experimental.securityindexing
        self.loadZCML(package=experimental.securityindexing)

    def setUpPloneSite(self, portal):
        self.applyProfile(portal, 'experimental.securityindexing:default')

    def tearDownZope(self, app):
        z2.uninstallProduct(app, 'experimental.securityindexing')


FIXTURE = SecurityIndexingLayer()
INTEGRATION = IntegrationTesting(
    bases=(FIXTURE,),
    name='SecurityIndexingLayer:Integration'
)
