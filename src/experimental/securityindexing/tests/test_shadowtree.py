import unittest

import mock

from BTrees.Interfaces import IDictionaryIsh
from zope.interface.verify import verifyObject

_PORTAL_ID = 'plone'


class _Dummy(object):

    def __init__(self, vpath, local_roles, local_roles_block=False):
        self.path = '/%s%s' % (_PORTAL_ID, vpath)
        self.aru = local_roles
        self.__ac_local_roles_block__ = local_roles_block
        self.id = self.path.split('/')[-1]

    # TODO: This class should probably define __ac_local_roles__
    #       to more closely simulate real plone objects.

    def __repr__(self):  # pragma: no cover
        return '_Dummy(%s)' % self.id

    __str__ = __repr__  # pragma: no cover

    def getId(self):
        return self.id

    def getPhysicalPath(self):
        return tuple(self.path.split('/'))


class TestShadowTreeNode(unittest.TestCase):

    plone_api_patcher_config = {
        'portal.get.return_value.getId.return_value': _PORTAL_ID
    }
    plone_api_patcher = mock.patch(
        'experimental.securityindexing.shadowtree.api',
        **plone_api_patcher_config
    )

    def _get_target_class(self):
        from ..shadowtree import Node
        return Node

    def _make_one(self, *args, **kw):
        cls = self._get_target_class()
        return cls(*args, **kw)

    def _create_security_token(self, obj, expected_type=int):
        Node = self._get_target_class()
        stoken = Node.create_security_token(obj)
        self.assertIsInstance(stoken, expected_type)
        return stoken

    def setUp(self):
        self.plone_api_patcher.start()

    def tearDown(self):
        self.plone_api_patcher.stop()

    def test_interface_conformant(self):
        verifyObject(IDictionaryIsh, self._make_one())

    def test__nonzero__(self):
        root = self._make_one()
        self.assertTrue(root)
        self.assertTrue(self._make_one(id='foo'))
        self.assertTrue(self._make_one(id='foo', parent=root))

    def test__len__(self):
        root = self._make_one()
        self.assertEqual(len(root), 0)
        names = ('a', 'b', 'c', 'd')
        for name in names:
            root[name] = self._make_one(id=name, parent=root)
        self.assertEqual(len(root), len(names))
        root['a']['b'] = self._make_one(id='x', parent=root['a'])
        self.assertEqual(len(root), len(names))
        self.assertEqual(len(root['a']), 1)

    def test__iter__(self):
        root = self._make_one()
        self.assertEqual(list(iter(root)), [])
        root['a'] = self._make_one(id='a', parent=root)
        self.assertEqual(list(iter(root)), ['a'])

    def test_create_security_token_on_attributeerror(self):
        local_roles = {'Role1', 'Role2'}
        obj1 = _Dummy('/a/b/c', local_roles, local_roles_block=False)
        obj2 = _Dummy('/a/b/c', local_roles, local_roles_block=True)
        dotted_name = 'experimental.securityindexing.shadowtree.api'
        with mock.patch(dotted_name) as patch:
            acl_users = patch.portal.get_tool.return_value
            acl_users._getAllLocalRoles.return_value = {
                'some_user_name_1_': local_roles
            }

            st1, st2 = map(self._create_security_token, (obj1, obj1))
            self.assertEqual(st1, st2)

            st1, st2 = map(self._create_security_token, (obj1, obj2))
            self.assertEqual(st1, st2)

        local_roles = {'Role1'}
        obj3 = _Dummy('/a/b/c', local_roles, local_roles_block=True)
        with mock.patch(dotted_name) as patch:
            acl_users = patch.portal.get_tool.return_value

            acl_users._getAllLocalRoles.return_value = {
                'some_user_name': {'Role1', 'Role2'}
            }
            st1 = self._create_security_token(obj2)

            acl_users._getAllLocalRoles.return_value = {
                'some_user_name': {'Role1'}
            }
            st2 = self._create_security_token(obj3)

            self.assertNotEqual(st1, st2)

    def test_update_security_info(self):
        root = self._make_one()
        node = self._make_one('foobar', parent=root)
        self.assertEqual(node.id, 'foobar')
        self.assertIs(node.__parent__, root)
        self.assertIsNone(node.token)
        self.assertIsNone(node.physical_path)
        self.assertFalse(node.block_inherit_roles)
        node.update_security_info(_Dummy('/foobar', ['Editor'],
                                         local_roles_block=True))
        self.assertEqual(node.id, 'foobar')
        self.assertIs(node.__parent__, root)
        self.assertIsInstance(node.token, int)
        self.assertEqual(node.physical_path, ('', 'plone', 'foobar'))
        self.assertTrue(node.block_inherit_roles)

    def test_ensure_ancestry_to_one_deep(self):
        root = self._make_one()
        dummy = _Dummy('/a', ['Anonymous'])
        leaf = root.ensure_ancestry_to(dummy)
        self.assertIn('a', root, list(root.keys()))
        self.assertEqual(root['a'].id, leaf.id)
        self.assertIsNone(leaf.__parent__.__parent__)
        self.assertIsNone(leaf.physical_path)
        self.assertEqual(leaf.id, 'a')
        self.assertIsNone(leaf.token)
        self.assertFalse(leaf.block_inherit_roles)

    def test_ensure_ancestry_to_many_deep(self):
        root = self._make_one()
        dummy = _Dummy('/a/b/c', ['Anonymous'])
        leaf = root.ensure_ancestry_to(dummy)

        b = leaf.__parent__
        self.assertEqual(b.id, 'b')
        self.assertIsNone(b.physical_path)
        self.assertIsNone(b.token)
        self.assertFalse(b.block_inherit_roles)

        a = b.__parent__
        self.assertEqual(a.id, 'a')
        self.assertIsNone(a.physical_path)
        self.assertIsNone(a.token)
        self.assertFalse(a.block_inherit_roles)

        self.assertEqual(leaf.__parent__.id, 'b')
        self.assertIsNone(leaf.physical_path)
        self.assertIsNone(leaf.token)
        self.assertFalse(leaf.block_inherit_roles)

    def test_ensure_ancestry_to_many_deep_no_change(self):
        root = self._make_one()
        dummy = _Dummy('/a/b/c', ['Anonymous'])
        leaf1 = root.ensure_ancestry_to(dummy)
        leaf2 = root.ensure_ancestry_to(dummy)
        self.assertIs(leaf1, leaf2)

    def test_ensure_ancestry_to_changes_leaf_only(self):
        root = self._make_one()
        dummy = _Dummy('/a/b/c', ['Anonymous'])
        leaf1 = root.ensure_ancestry_to(dummy)
        self.assertFalse(root['a']['b'].block_inherit_roles)
        root['a']['b'].block_inherit_roles = True
        leaf2 = root.ensure_ancestry_to(dummy)
        self.assertIs(leaf1, leaf2)
        self.assertTrue(root['a']['b'].block_inherit_roles)

    def test_descendants_empty(self):
        node = self._make_one('foo')
        self.assertEqual(list(node.descendants()), [])
        self.assertEqual(list(node.descendants(ignore_block=False)), [])

    def test_descendants_deep(self):
        root = self._make_one()
        dummy1 = _Dummy('/a/b/c1/d1/e1', ['Anonymous'])
        dummy2 = _Dummy('/a/b/c2/d2/e2/f2', ['Editor'])
        root.ensure_ancestry_to(dummy1)
        root.ensure_ancestry_to(dummy2)
        descendant_ids = list(node.id for node in root.descendants())
        expected_order = ['a', 'b', 'c1', 'd1', 'e1', 'c2', 'd2', 'e2', 'f2']
        self.assertEqual(descendant_ids, expected_order)

    def test_descendants_deep_with_ignore_block(self):
        root = self._make_one()
        dummy1 = _Dummy('/a/b/c1/d1/e1', ['Anonymous'])
        dummy2 = _Dummy('/a/b/c2/d2/e2/f2', ['Editor'])
        root.ensure_ancestry_to(dummy1)
        root.ensure_ancestry_to(dummy2)
        root['a']['b']['c2']['d2'].block_inherit_roles = True

        descendants = root.descendants(ignore_block=False)
        descendant_ids = list(node.id for node in descendants)
        expected_order = ['a', 'b', 'c1', 'd1', 'e1', 'c2']
        self.assertEqual(descendant_ids, expected_order)

        descendants = root.descendants(ignore_block=True)
        descendant_ids = list(node.id for node in descendants)
        expected_order = ['a', 'b', 'c1', 'd1', 'e1', 'c2', 'd2', 'e2', 'f2']
        self.assertEqual(descendant_ids, expected_order)
