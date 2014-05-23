import unittest

from plone import api
from zope.interface.verify import verifyObject, verifyClass
import plone.app.testing as pa_testing

from .. import testing
from ..interfaces import IObjectSecurity


class ObjectSecurityTestsMixin(testing.TestCaseMixin):

    def _get_target_class(self):
        from ..adapters import ObjectSecurity
        return ObjectSecurity

    def _make_one(self, *args, **kw):
        cls = self._get_target_class()
        return cls(*args, **kw)

    def _call_mut(self, obj, **kw):
        adapter = self._make_one(obj, self.catalog)
        adapter.reindex()
        self._check_shadowtree_nodes_have_security_info()

    def _check_catalog(self,
                       local_roles,
                       expected_paths,
                       search_operator=b'or'):
        pa_testing.logout()
        pa_testing.login(self.portal, self.query_user.getUserName())
        path_prefix = b'/%s' % (self.portal.getId(),)
        brains = self.catalog.unrestrictedSearchResults({
            b'path': path_prefix,
            b'allowedRolesAndUsers': {
                b'query': local_roles,
                b'operator': search_operator
            }
        })
        paths = set(brain.getPath().replace(path_prefix, b'')
                    for brain in brains)
        self._check_paths_equal(paths, expected_paths)

    def _populate(self):
        self.folders_by_path.clear()
        st_root = self._get_shadowtree_root()
        st_root.clear()
        create_folder = self._create_folder
        create_folder(b'/a', [b'Reader'], userid=b'matt')
        create_folder(b'/a/b', [b'Reader'])
        create_folder(b'/a/b/c', [b'Reader', b'Editor'])
        create_folder(b'/a/b/c/a', [b'Reader', b'Editor'])
        create_folder(b'/a/b/c/d', [b'Reader', b'Editor'])
        create_folder(b'/a/b/c/e', [b'Reader'], userid=b'liz', block=True)
        create_folder(b'/a/b/c/e/f', [b'Reader'])
        create_folder(b'/a/b/c/e/f/g', [b'Reviewer'])

    def setUp(self):
        super(ObjectSecurityTestsMixin, self).setUp()
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
        self._create_members(['matt', 'liz', 'guido'])
        api.user.grant_roles(username='matt', roles=[
            'Member', 'Contributor', 'Reader', 'Editor'
        ])
        pa_testing.setRoles(self.portal,
                            self.query_user.getUserId(),
                            ['Manager'])

    def test_interface_conformance(self):
        adapter_cls = self._get_target_class()
        verifyClass(IObjectSecurity, adapter_cls)
        folder = self._create_folder('/a', ['Reader'], userid='matt')
        verifyObject(IObjectSecurity, self._make_one(folder, self.catalog))

    def test_allowedRolesAndUsers(self):
        self._populate()
        check_catalog = self._check_catalog
        check_catalog(['user:' + self.query_user.getUserId()], set())
        check_catalog(['user:matt'], {
            '/a',
            '/a/b',
            '/a/b/c',
            '/a/b/c/a',
            '/a/b/c/d',
        })
        check_catalog(['user:liz'], {
            '/a/b/c/e',
            '/a/b/c/e/f',
            '/a/b/c/e/f/g',
        })
        check_catalog(['Reviewer'], set())
        check_catalog(['Editor'], set(self.folders_by_path))
        check_catalog(['Reader'], set(self.folders_by_path))

    def test_shadowtree_integrity(self):
        st_root = self._get_shadowtree_root()
        st_root.clear()
        check_shadowtree_integrity = self._check_shadowtree_paths
        check_shadowtree_integrity(st_root, set())
        self._populate()
        check_shadowtree_integrity(st_root, {
            tuple(b.getPath().split('/'))
            for b in self.catalog.unrestrictedSearchResults(path='/plone/a')
        })

        api.content.delete(self.portal['a']['b']['c']['d'])
        check_shadowtree_integrity(st_root, {
            tuple(b.getPath().split('/'))
            for b in self.catalog.unrestrictedSearchResults(path='/plone/a')
        })

    def _private_content_with_default_workflow(self):
        self._set_default_workflow_chain('plone_workflow')
        self._populate()
        for obj in self.folders_by_path.values():
            api.content.transition(obj, 'hide')

        # Logout, check that Anonymous cannot access any contents.
        pa_testing.logout()
        brains = self.catalog.searchResults()
        self.assertEqual(len(brains), 0)

    def test_reindex_on_workflow_transistion(self):
        # transition an object to published
        # check that children of object do not show up in
        # catalog search results.
        self._private_content_with_default_workflow()
        pa_testing.login(self.portal, pa_testing.TEST_USER_NAME)
        api.content.transition(self.folders_by_path['/a'], 'show')

        # Logout, check that we can access the item that's
        # been shown and nothing else.
        pa_testing.logout()
        brains = self.catalog.searchResults()
        self.assertEqual(brains[0].getPath(), '/plone/a')

    def test_reindex_on_grant_roles(self):
        pa_testing.login(self.portal, 'matt')
        self._private_content_with_default_workflow()

        pa_testing.login(self.portal, 'matt')
        obj = self.folders_by_path['/a/b']
        api.user.grant_roles(username='guido', obj=obj, roles=['Reader'])
        self._call_mut(obj)
        pa_testing.logout()

        pa_testing.login(self.portal, 'guido')
        brains = self.catalog.searchResults()
        actual = {b.getPath().replace('/plone', '') for b in brains}
        self.assertTrue(actual)
        self.assertSetEqual(actual, {
            '/a/b',
            '/a/b/c',
            '/a/b/c/a',
            '/a/b/c/d'
        })

    def test_reindex_on_revoke_roles(self):
        self._private_content_with_default_workflow()
        pa_testing.logout()
        pa_testing.login(self.portal, 'liz')
        brains = self.catalog.searchResults()
        actual = {b.getPath().replace('/plone', '') for b in brains}
        self.assertTrue(actual)
        self.assertSetEqual(actual, {
            '/a/b/c/e',
            '/a/b/c/e/f',
            '/a/b/c/e/f/g'
        })
        # Grant liz access to a node higher up
        obj = self.folders_by_path['/a/b/c']
        api.user.grant_roles(username='liz', obj=obj, roles=['Reader'])
        self._call_mut(obj)

        # Revoke liz's original access to e (and descendants)
        obj = self.folders_by_path['/a/b/c/e']

        api.user.revoke_roles(username='liz', obj=obj, roles=['Reader'])
        self._call_mut(obj)

        # Check liz can see everything under her granted
        # access *up until a local role block*
        brains = self.catalog.searchResults()
        actual = {b.getPath().replace('/plone', '') for b in brains}
        self.assertEqual(actual, {
            '/a/b/c',
            '/a/b/c/a',
            '/a/b/c/d'
        })

    def test_reindex_on_local_role_block_removal(self):
        self._private_content_with_default_workflow()
        obj = self.folders_by_path['/a']
        api.user.grant_roles(username='guido', obj=obj, roles=['Reader'])
        self._call_mut(obj)
        pa_testing.logout()

        pa_testing.login(self.portal, 'guido')
        brains = self.catalog.searchResults()
        actual = {b.getPath().replace('/plone', '') for b in brains}
        self.assertTrue(actual)
        self.assertSetEqual(actual, {
            '/a',
            '/a/b',
            '/a/b/c',
            '/a/b/c/a',
            '/a/b/c/d'
        })
        pa_testing.logout()

        pa_testing.login(self.portal, pa_testing.TEST_USER_NAME)
        obj = self.folders_by_path['/a/b/c/e']
        obj.__ac_local_roles_block__ = None
        self._call_mut(obj)
        pa_testing.logout()

        pa_testing.login(self.portal, 'guido')
        brains = self.catalog.searchResults()
        actual = {b.getPath().replace('/plone', '') for b in brains}
        self.assertSetEqual(actual, set(self.folders_by_path))


class TestObjectSecurity(ObjectSecurityTestsMixin, unittest.TestCase):

    layer = testing.INTEGRATION


class PatchedMixin(object):

    def _call_mut(self, obj, **kw):
        obj.reindexObjectSecurity(**kw)


class TestObjectSecurityPactched(PatchedMixin, TestObjectSecurity):
    """Run the tests under Archertypes with the monkey patched method."""


from plone.app.contenttypes.testing import (
    PLONE_APP_CONTENTTYPES_FIXTURE,
)

DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(PLONE_APP_CONTENTTYPES_FIXTURE, testing.FIXTURE),
    name=b'SecurityIndexingLayerDDCT:Integration'
)


class TestObjectSecurityDDCT(ObjectSecurityTestsMixin, unittest.TestCase):

    layer = DX_INTEGRATION

    def _check_paths_equal(self, paths, expected_paths):
        # Ignore robot-test-folder created by the
        # p.a.{event,contenttypes} fixture(s)
        exclude_path = b'/robot-test-folder'
        if exclude_path in paths:
            paths.remove(exclude_path)
        check = super(TestObjectSecurityDDCT, self)._check_paths_equal
        check(paths, expected_paths)


class TestObjectSecurityDDCTPactched(PatchedMixin, TestObjectSecurityDDCT):
    """Run the tests under Dexterity with the monkey patched method."""
