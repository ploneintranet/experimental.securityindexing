import unittest

from plone import api
import plone.app.testing as pa_testing

from .. import shadowtree, testing


class ObjectSecurityTestsMixin(object):
    """Tests for ObjectSecurityIndexer Adapter."""

    @property
    def portal(self):
        return self.layer['portal']

    def _create_folder(self, path, local_roles,
                       userid=pa_testing.TEST_USER_ID,
                       block=None):
        id = path.split('/')[-1]
        parent_path = filter(bool, path.split('/')[:-1])
        if parent_path:
            obj_path = '/%s' % '/'.join(parent_path)
            parent = api.content.get(path=obj_path)
        else:
            parent = self.portal
        folder = api.content.create(container=parent,
                                    type='Folder',
                                    id=id)
        api.user.grant_roles(username=userid,
                             obj=folder,
                             roles=local_roles)
        folder.__ac_local_roles_block__ = block
        self._call_mut(folder)
        self.folders_by_path[path] = folder

    def _populate(self):
        self.folders_by_path = {}
        create_folder = self._create_folder
        create_folder('/a', ['Reader'], userid='matt')
        create_folder('/a/b', ['Reader'])
        create_folder('/a/b/c', ['Reader', 'Editor'])
        create_folder('/a/b/c/a', ['Reader', 'Editor'])
        create_folder('/a/b/c/d', ['Reader', 'Editor'])
        create_folder('/a/b/c/e', ['Reader'], userid='liz', block=True)
        create_folder('/a/b/c/e/f', ['Reader'])
        create_folder('/a/b/c/e/f/g', ['Reviewer'])

    def _check_shadowtree_nodes_have_security_info(self):
        portal_id = self.portal.getId()
        for (path, obj) in sorted(self.folders_by_path.items(), key=len):
            node = shadowtree.get_root()
            path_components = list(filter(bool, obj.getPhysicalPath()))
            path_components.remove(portal_id)
            for path_component in path_components:
                node = node[path_component]
                self.assertTrue(hasattr(node, 'block_inherit_roles'))
                self.assertTrue(node.token,
                                msg='Node has no security info: %r' % node)
            self.assertEqual(node.physical_path, obj.getPhysicalPath())

    def _get_target_class(self):
        from ..adapters import ObjectSecurity
        return ObjectSecurity

    def _make_one(self, *args, **kw):
        cls = self._get_target_class()
        return cls(*args, **kw)

    def _call_mut(self, obj, **kw):
        catalog = api.portal.get_tool('portal_catalog')
        adapter = self._make_one(obj, catalog)
        adapter.reindex()
        self._check_shadowtree_nodes_have_security_info()

    def _query(self, local_roles, operator='or'):
        pa_testing.logout()
        pa_testing.login(self.portal, self.query_user.getUserName())
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.unrestrictedSearchResults({
            'allowedRolesAndUsers': {
                'query': local_roles,
                'operator': operator
            }
        })
        return brains

    def _check_catalog(self,
                       local_roles,
                       expected_paths,
                       search_operator='or'):
        brains = self._query(local_roles, operator=search_operator)
        prefix = '/%s' % self.portal.getId()
        paths = set(brain.getPath().replace(prefix, '') for brain in brains)
        self.assertSetEqual(paths, set(expected_paths))

    def _create_members(self, member_ids):
        for member_id in member_ids:
            email = '%s@plone.org' % member_id
            api.user.create(username=member_id, email=email)

    def setUp(self):
        portal = self.portal
        pa_testing.setRoles(portal, pa_testing.TEST_USER_ID, ['Manager'])
        pa_testing.login(portal, pa_testing.TEST_USER_NAME)
        wftool = api.portal.get_tool('portal_workflow')
        wftool.setDefaultChain('intranet_workflow')
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

    def test_allowedRolesAndUsers(self):
        self._populate()
        self._check_catalog(['user:' + self.query_user.getUserId()],
                            set())
        self._check_catalog(['user:matt'], {
            '/a',
            '/a/b',
            '/a/b/c',
            '/a/b/c/a',
            '/a/b/c/d',
        })
        self._check_catalog(['user:liz'], {
            '/a/b/c/e',
            '/a/b/c/e/f',
            '/a/b/c/e/f/g',
        })
        self._check_catalog(['Reviewer'], set())
        self._check_catalog(['Editor'], set(self.folders_by_path))
        self._check_catalog(['Reader'], set(self.folders_by_path))

    def _check_shadowtree_paths(self, expected_paths):
        root = shadowtree.get_root()
        shadow_paths = {
            node.physical_path
            for node in root.descendants(ignore_block=True)
        }
        self.assertSetEqual(shadow_paths, expected_paths)

    def test_shadowtree_integrity(self):
        catalog = api.portal.get_tool('portal_catalog')
        self._check_shadowtree_paths(set())

        self._populate()
        self._check_shadowtree_paths({
            tuple(b.getPath().split('/'))
            for b in catalog.unrestrictedSearchResults(path='/plone/a')
        })

        api.content.delete(self.portal['a']['b']['c']['d'])
        self._check_shadowtree_paths({
            tuple(b.getPath().split('/'))
            for b in catalog.unrestrictedSearchResults(path='/plone/a')
        })

    def _private_content_with_default_workflow(self):
        wftool = api.portal.get_tool('portal_workflow')
        wftool.setDefaultChain('plone_workflow')
        self._populate()
        for obj in self.folders_by_path.values():
            api.content.transition(obj, 'hide')

        # Logout, check that Anonymous cannot access any contents.
        pa_testing.logout()
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults()
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
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults()
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
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults()
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
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults()
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
        brains = catalog.searchResults()
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
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults()
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
        brains = catalog.searchResults()
        actual = {b.getPath().replace('/plone', '') for b in brains}
        self.assertSetEqual(actual, set(self.folders_by_path))


class TestObjectSecurityAT(ObjectSecurityTestsMixin, unittest.TestCase):

    layer = testing.AT_INTEGRATION


class _PatchedMixin(object):

    def _call_mut(self, obj, **kw):
        obj.reindexObjectSecurity(**kw)


class TestObjectSecurityATPatched(_PatchedMixin, TestObjectSecurityAT):
    """Run the tests with the monkey patched method."""


class TestObjectSecurityDX(ObjectSecurityTestsMixin, unittest.TestCase):

    layer = testing.DX_INTEGRATION

    def setUp(self):
        # Delete a fodler created by the p.a{contenttypes,event} fixtures
        super(TestObjectSecurityDX, self).setUp()
        api.content.delete(obj=self.portal['robot-test-folder'])


class TestObjectSecurityDXPatched(_PatchedMixin,
                                  TestObjectSecurityDX):
    """Run the tests with the monkey patched method."""
