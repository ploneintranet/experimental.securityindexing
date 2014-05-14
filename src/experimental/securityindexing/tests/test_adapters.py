from __future__ import print_function
import unittest

from plone import api
import plone.app.testing as pa_testing
import zope.component
import zope.interface

from .. import testing


class ARUIndexerTestsMixin(object):
    """Tests for ARUIndexer Adapter."""

    def __getattr__(self, name):
        try:
            return self.layer[name]
        except KeyError:
            raise AttributeError(name)

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
        folder.indexObject()
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

    def _get_target_class(self):
        from ..adapters import ARUIndexer
        return ARUIndexer

    def _make_one(self, *args, **kw):
        cls = self._get_target_class()
        return cls(*args, **kw)

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

    def _check_shadowtree_nodes_have_security_info(self, dummy):
        node = self._index.shadowtree
        for path_component in filter(bool, dummy.getPhysicalPath()):
            node = node[path_component]
            self.assertTrue(node.token,
                            msg='Node has no security info: %r' % node)

    def _check_catalog(self,
                       local_roles,
                       expected_paths,
                       search_operator='or'):
        brains = self._query(local_roles, operator=search_operator)
        prefix = '/%s' % self.portal.getId()
        paths = set(brain.getPath().replace(prefix, '') for brain in brains)
        self.assertSetEqual(paths, set(expected_paths))

    def _reindex_object_security(self, obj):
        catalog = api.portal.get_tool('portal_catalog')
        adapter = self._make_one(obj, catalog)
        adapter.reindexObjectSecurity()

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
        # Create a user that never is the Owner of
        # any objects created by this test.
        self.query_user = api.user.create(
            email='querier-test-user@netsight.co.uk',
            username='querier-test-user'
        )
        self._create_members(['matt', 'liz', 'guido'])
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
        from .. import shadowtree
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

    def test_reindexObjectSecurity(self):
        self._populate()
        paths = {
            '/a',
            '/a/b',
            '/a/b/c',
            '/a/b/c/a',
            '/a/b/c/d'
        }
        self._check_catalog(['user:matt'], paths)
        obj = self.folders_by_path['/a/b/c/d']
        api.user.revoke_roles(username='matt',
                              obj=obj,
                              roles=['Reader', 'Editor'])
        api.user.grant_roles(username='liz',
                             obj=obj,
                             roles=['Contributor'])
        self._reindex_object_security(obj)
        self._check_catalog(['user:liz'], paths)
        self._check_catalog(['user:matt'], paths - {'/a/b/c/d'})
        return
        self._effect_change(
            4,
            _Dummy('/a/b/c/d', ['Anonymous', 'Authenticated', 'Editor'])
        )
        self._check_index(['Anonymous', 'Authenticated'],
                          [2, 3, 4, 5],
                          operator='and')
        self._check_index(['Editor'], [4], operator='and')
        self._effect_change(
            2,
            _Dummy('/a/b/c', ['Contributor'])
        )
        self._check_index(['Contributor'], {2})
        self._check_index(['Anonymous', 'Authenticated'], {3, 4, 5},
                          operator='and')

    def test__index_object_on_change_recurse(self):
        self._populate()
        self._values[2].aru = ['Contributor']
        dummy = self._values[2]
        zope.interface.alsoProvides(dummy, IDecendantLocalRolesAware)
        self._effect_change(2, dummy)
        self._check_index(['Contributor'], {2, 3, 4}, dummy=dummy)
        self._check_index(['Anonymous', 'Authenticated'],
                          {0, 1, 5, 6},
                          dummy=dummy)

    def test_reindex_no_change(self):
        self._populate()
        obj = self._values[7]
        self._effect_change(7, obj)
        self._check_index(['Reviewer'], {7})
        self._effect_change(7, obj)
        self._check_index(['Reviewer'], {7})

    def test_index_object_when_raising_attributeerror(self):
        class FauxObject(_Dummy):
            def allowedRolesAndUsers(self):
                raise AttributeError
        to_index = FauxObject('/a/b', ['Role'])
        self._index.index_object(10, to_index)
        self.assertFalse(self._index._unindex.get(10))
        self.assertFalse(self._index.getEntryForObject(10))

    def test_index_object_when_raising_typeeror(self):
        class FauxObject(_Dummy):
            def allowedRolesAndUsers(self, name):
                return 'allowedRolesAndUsers'

        to_index = FauxObject('/a/b', ['Role'])
        self._index.index_object(10, to_index)
        self.assertFalse(self._index._unindex.get(10))
        self.assertFalse(self._index.getEntryForObject(10))

    def test_value_removes(self):
        to_index = _Dummy('/a/b/c', ['hello'])
        self._index.index_object(10, to_index)
        self.assertIn(10, self._index._unindex)

        to_index = _Dummy('/a/b/c', [])
        self._index.index_object(10, to_index)
        self.assertNotIn(10, self._index._unindex)


class TestARUIndexerDX(ARUIndexerTestsMixin, unittest.TestCase):

    layer = testing.DX_INTEGRATION

    def setUp(self):
        # Delete a fodler created by the p.a{contenttypes,event} fixtures
        super(TestARUIndexerDX, self).setUp()
        api.content.delete(obj=self.portal['robot-test-folder'])


class TestARUIndexerAT(ARUIndexerTestsMixin, unittest.TestCase):

    layer = testing.AT_INTEGRATION


if __name__ == '__main__':
    unittest.main()
