from __future__ import print_function

from plone.app.contenttypes.testing import (
    PLONE_APP_CONTENTTYPES_FIXTURE,
)
from plone.app.event.testing import PAEvent_FIXTURE
import plone.app.testing as pa_testing


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


class DXIntegrationLayer(SecurityIndexingLayerMixin,
                         pa_testing.PloneSandboxLayer):
    """A layer for Dexterity integration testing."""

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE,
                    PAEvent_FIXTURE,
                    pa_testing.PLONE_FIXTURE)


class ATIntegrationLayer(SecurityIndexingLayerMixin,
                         pa_testing.PloneSandboxLayer):
    """A layer for Archetypes integration testing."""


AT_FIXTURE = ATIntegrationLayer()
AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_FIXTURE,),
    name='ATIntegrationLayer:Integration'
)

DX_FIXTURE = DXIntegrationLayer()
DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_FIXTURE,),
    name='DXIntegrationLayer:Integration'
)
