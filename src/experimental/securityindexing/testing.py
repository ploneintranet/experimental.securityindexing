import plone.app.testing as pa_testing


class SecurityIndexingInstalledLayer(object):
    """Mixin for layers."""

    def setUpZope(self, app, configuration_context):
        super(
            SecurityIndexingInstalledLayer, 
            self
        ).setUpZope(app, configuration_context)
        # Load ZCML
        import experimental.securityindexing
        self.loadZCML(package=experimental.securityindexing,
                      context=configuration_context)

    def setUpPloneSite(self, portal):
        super(
            SecurityIndexingInstalledLayer, 
            self
        ).setUpPloneSite(portal)
        self.applyProfile(portal, 'experimental.securityindexing:default')


class SecurityIndexingLayer(SecurityIndexingInstalledLayer, 
                            pa_testing.PloneSandboxLayer):

    defaultBases = (pa_testing.PLONE_FIXTURE,)


FIXTURE = SecurityIndexingLayer()

INTEGRATION = pa_testing.IntegrationTesting(
    bases=(FIXTURE,),
    name='SecurityIndexingLayer:Integration'
)

