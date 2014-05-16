from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
from plone.app.event.testing import PAEvent_FIXTURE
from plone.testing import z2
import plone.app.testing as pa_testing


class SecurityIndexingLayerMixin(object):
    """Mixin for layers."""

    def _check_shadowtree_deleted(self, app):
        from . import shadowtree
        storage = shadowtree.Node._get_storage(context=app.plone)
        assert __package__ not in storage, list(storage.keys())

    def setUpZope(self, app, configuration_context):
        super(SecurityIndexingLayerMixin, self).setUpZope(
            app,
            configuration_context
        )
        import experimental.securityindexing as package
        self.loadZCML(package=package,
                      context=configuration_context)

    def tearDownZope(self, app):
        super(SecurityIndexingLayerMixin, self).tearDownZope(app)
        z2.uninstallProduct(app, 'experimental.securityindexing')
        self._check_shadowtree_deleted(app)

    def setUpPloneSite(self, portal):
        super(SecurityIndexingLayerMixin, self).setUpPloneSite(portal)
        self.applyProfile(portal, 'experimental.securityindexing:default')

    def tearDownPloneSite(self, portal):
        super(SecurityIndexingLayerMixin, self).tearDownPloneSite(portal)
        self.applyProfile(portal, 'experimental.securityindexing:uninstall')


class ATIntegrationLayer(SecurityIndexingLayerMixin,
                         pa_testing.PloneSandboxLayer):
    """A layer for Archetypes integration testing."""

    defaultBases = (pa_testing.PLONE_FIXTURE,)


class DXIntegrationLayer(SecurityIndexingLayerMixin,
                         pa_testing.PloneSandboxLayer):
    """A layer for Dexterity integration testing."""

    defaultBases = (
        PLONE_APP_CONTENTTYPES_FIXTURE,
        PAEvent_FIXTURE,
        pa_testing.PLONE_FIXTURE
    )


AT_FIXTURE = ATIntegrationLayer()
AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_FIXTURE,),
    name='%s.ATIntegrationLayer:Integration' % __package__
)

DX_FIXTURE = DXIntegrationLayer()
DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_FIXTURE,),
    name='%s.DXIntegrationLayer:Integration' % __package__
)
