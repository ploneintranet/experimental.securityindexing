from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting

from plone.testing import z2


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
