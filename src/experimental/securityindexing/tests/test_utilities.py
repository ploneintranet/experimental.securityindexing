import unittest

import mock
from zope.interface.verify import verifyObject

from .utils import FakePlonePortal
from ..interfaces import IShadowTree, IShadowTreeTool


class TestShadowTreeTool(unittest.TestCase):

    _fake_portal = FakePlonePortal()

    plone_api_patcher_config = {
        'portal.get.return_value': _fake_portal
    }

    plone_api_patcher = mock.patch(
        'experimental.securityindexing.utilities.api',
        **plone_api_patcher_config
    )

    def setUp(self):
        self.plone_api_patcher.start()

    def tearDown(self):
        self.plone_api_patcher.stop()

    def _get_target_class(self):
        from ..utilities import ShadowTreeTool
        return ShadowTreeTool

    def _make_one(self, *args, **kw):
        utility = self._get_target_class()
        return utility()

    def test_interface_conformance(self):
        util = self._make_one()
        verifyObject(IShadowTreeTool, util)

    def test_root(self):
        util = self._make_one()
        self.assertTrue(IShadowTree.providedBy(util.root))
