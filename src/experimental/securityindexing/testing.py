from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
import plone.app.testing as pa_testing


class SecurityIndexingLayerMixin(object):
    """Mixin for layers."""

    def setUpZope(self, app, configuration_context):
        super(SecurityIndexingLayerMixin, self).setUpZope(
            app,
            configuration_context
        )
        import experimental.securityindexing as package
        self.loadZCML(package=package,
                      context=configuration_context)

    def setUpPloneSite(self, portal):
        super(SecurityIndexingLayerMixin, self).setUpPloneSite(portal)
        self.applyProfile(portal, 'experimental.securityindexing:default')

    def tearDownPloneSite(self, portal):
        self.applyProfile(portal, 'experimental.securityindexing:uninstall')
        super(SecurityIndexingLayerMixin, self).tearDownPloneSite(portal)


class ATIntegrationLayer(SecurityIndexingLayerMixin,
                         pa_testing.PloneSandboxLayer):
    """A layer for Archetypes integration testing."""

    defaultBases = (pa_testing.PLONE_FIXTURE,)


class DXIntegrationLayer(SecurityIndexingLayerMixin,
                         pa_testing.PloneSandboxLayer):
    """A layer for Dexterity integration testing."""

    defaultBases = (
        PLONE_APP_CONTENTTYPES_FIXTURE,
        pa_testing.PLONE_FIXTURE
    )


AT_FIXTURE = ATIntegrationLayer()
AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_FIXTURE,),
    name='%s.B_ATIntegrationLayer:Integration' % __package__
)

DX_FIXTURE = DXIntegrationLayer()
DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_FIXTURE,),
    name='%s.A_DXIntegrationLayer:Integration' % __package__
)
