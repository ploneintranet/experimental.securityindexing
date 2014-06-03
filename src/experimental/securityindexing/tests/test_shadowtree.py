import unittest

import mock

from .utils import FakePlonePortal


_PORTAL_ID = b'plone'


class _Dummy(object):

    def __init__(self, vpath, local_roles, local_roles_block=False):
        self.path = b'/%s%s' % (_PORTAL_ID, vpath)
        self.aru = local_roles
        self.__ac_local_roles_block__ = local_roles_block
        self.id = self.path.split(b'/')[-1]

    # TODO: This class should probably define __ac_local_roles__
    #       to more closely simulate real plone objects.

    def __repr__(self):  # pragma: no cover
        return b'_Dummy(%s)' % self.id

    __str__ = __repr__  # pragma: no cover

    def getPhysicalPath(self):
        return tuple(self.path.split(b'/'))


class TestShadowTreeNode(unittest.TestCase):

    _fake_portal = FakePlonePortal()

    plone_api_patcher_config = {
        b'portal.get.return_value': _fake_portal
    }

    plone_api_patcher = mock.patch(
        b'experimental.securityindexing.shadowtree.api',
        **plone_api_patcher_config
    )

    def _get_target_class(self):
        from ..shadowtree import Node
        return Node

    def _make_one(self, asroot=True, *args, **kw):
        cls = self._get_target_class()
        node = cls(*args, **kw)
        return node

    def _create_security_token(self, obj, expected_type=int):
        Node = self._get_target_class()
        stoken = Node.create_security_token(obj)
        self.assertIsInstance(stoken, expected_type)
        return stoken

    def setUp(self):
        self.plone_api_patcher.start()

    def tearDown(self):
        self.plone_api_patcher.stop()
        self._fake_portal.clear()

    def test__nonzero__(self):
        root = self._make_one()
        self.assertTrue(root)
        self.assertTrue(self._make_one(id=b'foo'))
        self.assertTrue(self._make_one(id=b'foo', parent=root))

    def test__len__(self):
        root = self._make_one()
        self.assertEqual(len(root), 0)
        names = (b'a', b'b', b'c', b'd')
        for name in names:
            root[name] = self._make_one(id=name, parent=root)
        self.assertEqual(len(root), len(names))
        root[b'a'][b'b'] = self._make_one(id=b'x', parent=root[b'a'])
        self.assertEqual(len(root), len(names))
        self.assertEqual(len(root[b'a']), 1)

    def test__iter__(self):
        root = self._make_one()
        self.assertEqual(list(iter(root)), [])
        root[b'a'] = self._make_one(id=b'a', parent=root)
        self.assertEqual(list(iter(root)), [b'a'])

    def test__getattr__(self):
        root = self._make_one()
        with self.assertRaises(AttributeError):
            root.foo
        # check some OOBTree attributes are found
        self.assertTrue(getattr(root, b'keys', None))
        self.assertTrue(getattr(root, b'minKey', None))
        getattr(root, b'_p_changed')

    def test_interface_conformance(self):
        import BTrees
        from zope import interface
        from zope.interface.verify import verifyClass, verifyObject
        from zope.interface.exceptions import DoesNotImplement, Invalid
        from ..interfaces import IShadowTreeNode, IShadowTreeRoot

        # Default node creation
        Node = self._get_target_class()
        verifyClass(IShadowTreeNode, Node)

        # Creating a node with no id or parent implies
        # intent to create the root node.
        node = self._make_one()
        verifyObject(IShadowTreeNode, node)
        verifyObject(BTrees.Interfaces.IBTree, node)

        # Regular nodes must be contained.
        with self.assertRaises(Invalid):
            IShadowTreeNode.validateInvariants(node)

        # Utiltiies that provide the root node
        # should declare they do so...
        with self.assertRaises(DoesNotImplement):
            verifyObject(IShadowTreeRoot, node)

        # root node must have empty ids.
        root = self._make_one(id='ROOTME.')
        with self.assertRaises(Invalid):
            IShadowTreeRoot.validateInvariants(root)

        root = self._make_one()
        interface.alsoProvides(root, IShadowTreeRoot)
        verifyObject(IShadowTreeRoot, root)
        IShadowTreeRoot.validateInvariants(root)

        node = self._make_one(id='a1', parent=root)
        IShadowTreeNode.validateInvariants(node)
        with self.assertRaises(Invalid):
            IShadowTreeRoot.validateInvariants(node)

    def test_create_security_token_on_attributeerror(self):
        local_roles = {b'Role1', b'Role2'}
        obj1 = _Dummy(b'/a/b/c', local_roles, local_roles_block=False)
        obj2 = _Dummy(b'/a/b/c', local_roles, local_roles_block=True)
        dotted_name = 'experimental.securityindexing.shadowtree.api'
        with mock.patch(dotted_name) as patch:
            acl_users = patch.portal.get_tool.return_value
            acl_users._getAllLocalRoles.return_value = {
                b'some_user_name_1_': local_roles
            }

            st1, st2 = map(self._create_security_token, (obj1, obj1))
            self.assertEqual(st1, st2)

            st1, st2 = map(self._create_security_token, (obj1, obj2))
            self.assertEqual(st1, st2)

        local_roles = {b'Role1'}
        obj3 = _Dummy(b'/a/b/c', local_roles, local_roles_block=True)
        with mock.patch(dotted_name) as patch:
            acl_users = patch.portal.get_tool.return_value

            acl_users._getAllLocalRoles.return_value = {
                b'some_user_name': {b'Role1', b'Role2'}
            }
            st1 = self._create_security_token(obj2)

            acl_users._getAllLocalRoles.return_value = {
                b'some_user_name': {b'Role1'}
            }
            st2 = self._create_security_token(obj3)

            self.assertNotEqual(st1, st2)

    def test_update_security_info(self):
        root = self._make_one()
        node = self._make_one(id=b'foobar', parent=root)
        self.assertEqual(node.id, b'foobar')
        self.assertIs(node.__parent__, root)
        self.assertIsNone(node.token)
        self.assertIsNone(node.physical_path)
        self.assertFalse(node.block_inherit_roles)
        node.update_security_info(_Dummy(b'/foobar', [b'Editor'],
                                         local_roles_block=True))
        self.assertEqual(node.id, b'foobar')
        self.assertIs(node.__parent__, root)
        self.assertIsInstance(node.token, int)
        self.assertEqual(node.physical_path, (b'', b'plone', b'foobar'))
        self.assertTrue(node.block_inherit_roles)

    def test_ensure_ancestry_to_one_deep(self):
        root = self._make_one()
        dummy = _Dummy(b'/a', [b'Anonymous'])
        leaf = root.ensure_ancestry_to(dummy)
        self.assertIn(b'a', root, list(root.keys()))
        self.assertEqual(root[b'a'].id, leaf.id)
        self.assertIsNone(leaf.__parent__.__parent__)
        self.assertEqual(leaf.physical_path, ('', 'plone', 'a'))
        self.assertEqual(leaf.id, b'a')
        self.assertIsNone(leaf.token)
        self.assertFalse(leaf.block_inherit_roles)

    def test_ensure_ancestry_to_many_deep(self):
        root = self._make_one()
        dummy = _Dummy('/a/b/c', ['Anonymous'])
        leaf = root.ensure_ancestry_to(dummy)

        b = leaf.__parent__
        self.assertEqual(b.id, b'b')
        self.assertIsNone(b.physical_path)
        self.assertIsNone(b.token)
        self.assertFalse(b.block_inherit_roles)

        a = b.__parent__
        self.assertEqual(a.id, b'a')
        self.assertIsNone(a.physical_path)
        self.assertIsNone(a.token)
        self.assertFalse(a.block_inherit_roles)

        self.assertEqual(leaf.__parent__.id, b'b')
        self.assertEqual(leaf.physical_path, ('', 'plone', 'a', 'b', 'c'))
        self.assertIsNone(leaf.token)
        self.assertFalse(leaf.block_inherit_roles)

    def test_ensure_ancestry_to_many_deep_no_change(self):
        root = self._make_one()
        dummy = _Dummy(b'/a/b/c', [b'Anonymous'])
        leaf1 = root.ensure_ancestry_to(dummy)
        leaf2 = root.ensure_ancestry_to(dummy)
        self.assertIs(leaf1, leaf2)

    def test_ensure_ancestry_to_changes_leaf_only(self):
        root = self._make_one()
        dummy = _Dummy(b'/a/b/c', [b'Anonymous'])
        leaf1 = root.ensure_ancestry_to(dummy)
        self.assertFalse(root[b'a'][b'b'].block_inherit_roles)
        root[b'a'][b'b'].block_inherit_roles = True
        leaf2 = root.ensure_ancestry_to(dummy)
        self.assertIs(leaf1, leaf2)
        self.assertTrue(root[b'a'][b'b'].block_inherit_roles)

    def test_descendants_empty(self):
        node = self._make_one(b'foo')
        self.assertEqual(list(node.descendants()), [])
        self.assertEqual(list(node.descendants(ignore_block=False)), [])

    def test_descendants_deep(self):
        root = self._make_one()
        dummy1 = _Dummy('/a/b/c1/d1/e1', ['Anonymous'])
        dummy2 = _Dummy('/a/b/c2/d2/e2/f2', ['Editor'])
        root.ensure_ancestry_to(dummy1)
        root.ensure_ancestry_to(dummy2)
        descendant_ids = list(node.id for node in root.descendants())
        expected_order = [b'a', b'b', b'c1', b'd1', b'e1',
                          b'c2', b'd2', b'e2', b'f2']
        self.assertEqual(descendant_ids, expected_order)

    def test_descendants_deep_with_ignore_block(self):
        root = self._make_one()
        dummy1 = _Dummy(b'/a/b/c1/d1/e1', [b'Anonymous'])
        dummy2 = _Dummy(b'/a/b/c2/d2/e2/f2', [b'Editor'])
        root.ensure_ancestry_to(dummy1)
        root.ensure_ancestry_to(dummy2)
        root[b'a'][b'b'][b'c2'][b'd2'].block_inherit_roles = True

        descendants = root.descendants(ignore_block=False)
        descendant_ids = list(node.id for node in descendants)
        expected_order = [b'a', b'b', b'c1', b'd1', b'e1', b'c2']
        self.assertEqual(descendant_ids, expected_order)
        descendants = root.descendants(ignore_block=True)
        descendant_ids = list(node.id for node in descendants)
        expected_order = [b'a', b'b', b'c1', b'd1', b'e1',
                          b'c2', b'd2', b'e2', b'f2']
        self.assertEqual(descendant_ids, expected_order)

    def test_delete_node(self):
        root = self._make_one()
        dummy1 = _Dummy(b'/a/b/c/d', [b'Reader'])
        dummy2 = _Dummy(b'/a/b/c/d/e', [b'Editor'])
        dummy3 = _Dummy(b'/a/b/c/d/e/f', [b'Editor'])
        node1 = root.ensure_ancestry_to(dummy1)
        node2 = root.ensure_ancestry_to(dummy2)
        root.ensure_ancestry_to(dummy3)
        del node1[node2.id]
        self.assertRaises(LookupError, root.traverse, b'/a/b/c/d/e/f')
        self.assertRaises(LookupError, root.traverse, b'/a/b/c/d/e')
        root.traverse(dummy1.getPhysicalPath())

    def test_traverse(self):
        root = self._make_one()
        self.assertRaises(TypeError, root.traverse, None)
        self.assertRaises(TypeError, root.traverse, object())
        dummy1 = _Dummy(b'/a/b/c1/d1/e1', [b'Anonymous'])
        dummy2 = _Dummy(b'/a/b/c2/d2/e2/f2', [b'Editor'])
        dummy3 = _Dummy(b'/a/b/c2/d2/e3/f3', [b'Editor'])
        root.ensure_ancestry_to(dummy1)
        root.ensure_ancestry_to(dummy2)
        node = root.ensure_ancestry_to(dummy3)
        t_node = root.traverse(b'/a/b/c2/d2/e3/f3')
        self.assertIs(t_node, node)
        t_node = root.traverse(b'/a/b/c2/d2/e3')
        self.assertIs(t_node, node.__parent__)

        self.assertRaises(LookupError, node.traverse, '/')
        self.assertRaises(LookupError, root.traverse, '../')

        # test with tuples
        self.assertRaises(LookupError, root.traverse, ())
        self.assertIs(root.traverse(('',)), root)
        t_node = root.traverse(tuple(b'/a/b/c2/d2/e3/f3'.split('/')))
        self.assertIs(t_node, node)
