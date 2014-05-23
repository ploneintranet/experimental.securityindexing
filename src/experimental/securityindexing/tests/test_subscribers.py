import unittest

import plone.api as api
import plone.app.testing as pa_testing

from .. import testing


class SubscriberTests(testing.TestCaseMixin, unittest.TestCase):

    layer = testing.INTEGRATION

    def _call_mut(self, *args, **kw):
        # Subscribers are automatically invoked
        pass

    def _populate(self):
        self.folders_by_path.clear()
        st_root = self._get_shadowtree_root()
        st_root.clear()
        create_folder = self._create_folder
        create_folder(b'/x', [b'Reader'], userid=b'bob')
        create_folder(b'/x/y', [b'Reader'])
        create_folder(b'/x/y/z', [b'Reader', b'Editor'])
        create_folder(b'/x/y/z/a', [b'Reader', b'Editor'])
        create_folder(b'/x/b', [b'Reader'], userid=b'jane', block=True)
        create_folder(b'/x/b/c', [b'Reader'])
        create_folder(b'/x/b/c/d', [b'Reviewer'], userid='bob')

    def setUp(self):
        super(SubscriberTests, self).setUp()
        portal = self.portal
        pa_testing.setRoles(portal, pa_testing.TEST_USER_ID, ['Manager'])
        pa_testing.login(portal, pa_testing.TEST_USER_NAME)
        self._set_default_workflow_chain('intranet_workflow')
        # Create a user that never is owns
        # any objects created by this test.
        self.query_user = api.user.create(
            email='querier-test-user@netsight.co.uk',
            username='querier-test-user'
        )
        self._create_members(['bob', 'jane'])
        api.user.grant_roles(username='bob', roles=[
            'Member', 'Contributor', 'Reader', 'Editor'
        ])
        pa_testing.setRoles(self.portal,
                            self.query_user.getUserId(),
                            ['Manager'])

    def test_on_object_added(self):
        self._populate()
        self._check_shadowtree_integrity()

    def test_on_object_removed(self):
        self._populate()
        self._check_shadowtree_integrity()
        api.content.delete(self.folders_by_path[b'/x/y/z/a'])

    def test_on_object_removed_is_at_content_root(self):
        self._populate()
        self._check_shadowtree_integrity()
        api.content.delete(self.folders_by_path[b'/x'])
        self._check_shadowtree_integrity()
