import unittest

import mock

from .utils import FakePlonePortal


class TestShadowTreeTool(unittest.TestCase):

    _fake_portal = FakePlonePortal()
    _package = b'experimental.securityindexing'

    plone_api_patcher_config = {
        b'portal.get.return_value': _fake_portal
    }

    plone_api_patcher = mock.patch(
        b'%s.utilities.api' % (_package,),
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
        from zope.interface.verify import verifyClass, verifyObject
        from ..interfaces import IShadowTreeTool
        verifyClass(IShadowTreeTool, self._get_target_class())
        util = self._make_one()
        verifyObject(IShadowTreeTool, util)
        IShadowTreeTool.validateInvariants(util)

    def test_root(self):
        from ..interfaces import IShadowTreeRoot
        util = self._make_one()
        self.assertTrue(IShadowTreeRoot.providedBy(util.root))

    def test_delete_from_storage(self):
        tool_cls = self._get_target_class()
        storage = tool_cls._get_storage(portal=self._fake_portal)

        # ensure the root node is stored.
        self._make_one().root
        self.assertIn(self._package, storage)

        # check it's gone when it's supposed to be.
        tool_cls.delete_from_storage(self._fake_portal)
        self.assertNotIn(self._package, storage)
