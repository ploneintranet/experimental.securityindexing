import random
import unittest

import plone.api as api
import plone.app.testing as pa_testing
import transaction

from . import dx
from .. import testing


class SubscriberTestsMixin(testing.TestCaseMixin):

    def _id_for_path(self, path):
        u"""Modifies the id used for the folder id to simulate renaming."""
        id = super(SubscriberTestsMixin, self)._id_for_path(path)
        suffix = random.randint(1000, 1000 + len(self.folders_by_path))
        return b'%s.%s' % (id, suffix)

    def _create_folder(self, path, local_roles,
                       userid=pa_testing.TEST_USER_ID,
                       block=False):
        u"""Create a folder then rename it to cause the
        relevant events to be fired as if this were done TTW.
        """
        create_folder = super(SubscriberTestsMixin, self)._create_folder
        create_folder(path, local_roles, userid=userid, block=block)
        # need to involve transaction so that we can rename
        # - use savepoint rather than commit
        #   since we are in an integration layer
        #   are transaction scope is per-test
        transaction.savepoint()
        folder = self.folders_by_path[path]
        new_id = folder.getId().split(b'.')[0]
        with api.env.adopt_user(username=pa_testing.TEST_USER_NAME):
            api.content.rename(obj=folder, new_id=new_id)

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
        super(SubscriberTestsMixin, self).setUp()
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

    def test_on_object_moved(self):
        self._populate()
        self._check_shadowtree_integrity()

    def test_on_object_removed(self):
        self._populate()
        self._check_shadowtree_integrity()
        api.content.delete(obj=self.folders_by_path[b'/x/y/z/a'])

    def test_on_object_removed_is_at_content_root(self):
        self._populate()
        self._check_shadowtree_integrity()
        api.content.delete(obj=self.folders_by_path[b'/x'])
        self._check_shadowtree_integrity()


class TestSubscribers(SubscriberTestsMixin, unittest.TestCase):

    layer = testing.INTEGRATION


class TestSubscribersDDCT(dx.Mixin,
                          SubscriberTestsMixin,
                          unittest.TestCase):
    layer = dx.INTEGRATION
