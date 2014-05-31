import unittest

import plone.app.testing as pa_testing
import plone.api as api

from .. import testing


class UninstallableLayer(testing.SecurityIndexingLayer):

    def tearDownPloneSite(self, portal):
        pass

    def tearDownZope(self, app):
        pass


UNINSTALL_FIXTURE = UninstallableLayer()


class TestUninstall(testing.TestCaseMixin, unittest.TestCase):
    u"""Tests that this package can be uninstalled.

    This uses the ``quick installer`` tool,  which is used by
    both the ZMI and overview-contrpanel (aka plone_control_panel).
    """

    layer = pa_testing.IntegrationTesting(
        bases=(UNINSTALL_FIXTURE,),
        name=b'SecurityIndexingUninstallLayer:Integration')

    def runTest(self):
        pkg = __package__.rsplit(b'.', 1)[0]
        qi_tool = api.portal.get_tool(name=b'portal_quickinstaller')
        qi_tool.uninstallProducts([pkg])
        self.assertFalse(qi_tool.isProductInstalled(pkg))
        self.assertTrue(qi_tool.isProductInstallable(pkg))
        self.assertNotIn(pkg, qi_tool.getBrokenInstalls())
        with self.assertRaises(api.exc.InvalidParameterError):
            api.portal.get_tool(name=b'portal_shadowtree')
