import unittest


from .. import testing


class _Dummy(object):

    def __init__(self, path, local_roles, local_roles_block=False):
        self.path = path
        self.aru = local_roles
        self.__ac_local_roles_block__ = local_roles_block
        self.id = path.split('/')[-1]

    def __str__(self):
        return '<Dummy: %s>' % self.id

    __repr__ = __str__

    def getId(self):
        return self.id

    def getPhysicalPath(self):
        return tuple(self.path.split('/'))

    def allowedRolesAndUsers(self):
        return self.aru


class TestShadowTreeNode(unittest.TestCase):

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

    def test_create_security_token_on_attributeerror(self):
        obj1 = _Dummy('/a/b/c', ['Role1', 'Role2'], local_roles_block=False)
        st1, st2 = map(self._create_security_token, (obj1, obj1))
        self.assertEqual(st1, st2)

        obj2 = _Dummy('/a/b/c', ['Role1', 'Role2'], local_roles_block=True)
        st1, st2 = map(self._create_security_token, (obj1, obj2))
        self.assertNotEqual(st1, st2)

        obj3 = _Dummy('/a/b/c', ['Role1'], local_roles_block=True)
        st1, st2 = map(self._create_security_token, (obj2, obj3))
        self.assertNotEqual(st1, st2)

        # TODO: Is it guarenteed that ARU will be in the same order?
        #       i.e Is security token for [r1, r2] to be
        #       considered same as one for to [r2, r1]?

    def test_update_security_info(self):
        root = self._make_one()
        node = self._make_one('foobar', parent=root)
        self.assertEqual(node.id, 'foobar')
        self.assertIs(node.__parent__, root)
        self.assertIsNone(node.token)
        self.assertIsNone(node.physical_path)
        self.assertFalse(node.block_inherit_roles)
        self.assertIsNone(node.document_id)
        node.update_security_info(1, _Dummy('/foobar', ['Editor'],
                                           local_roles_block=True))
        self.assertEqual(node.document_id, 1)
        self.assertEqual(node.id, 'foobar')
        self.assertIs(node.__parent__, root)
        self.assertIsInstance(node.token, int)
        self.assertEqual(node.physical_path, ('', 'foobar'))
        self.assertTrue(node.block_inherit_roles)

    def test_ensure_ancestry_to_one_deep(self):
        root = self._make_one()
        dummy = _Dummy('/a', ['Anonymous'])
        Node = self._get_target_class()
        leaf = Node.ensure_ancestry_to(dummy, root)
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
        Node = self._get_target_class()
        leaf = Node.ensure_ancestry_to(dummy, root)

        b = leaf.__parent__
        self.assertEqual(b.id, 'b')
        self.assertIsNone(b.document_id)
        self.assertIsNone(b.physical_path)
        self.assertIsNone(b.token)
        self.assertFalse(b.block_inherit_roles)

        a = b.__parent__
        self.assertEqual(a.id, 'a')
        self.assertIsNone(a.document_id)
        self.assertIsNone(a.physical_path)
        self.assertIsNone(a.token)
        self.assertFalse(a.block_inherit_roles)

        self.assertEqual(leaf.__parent__.id, 'b')
        self.assertIsNone(leaf.document_id)
        self.assertIsNone(leaf.physical_path)
        self.assertIsNone(leaf.token)
        self.assertFalse(leaf.block_inherit_roles)

    def test_ensure_ancestry_to_many_deep_no_change(self):
        root = self._make_one()
        dummy = _Dummy('/a/b/c', ['Anonymous'])
        Node = self._get_target_class()
        leaf1 = Node.ensure_ancestry_to(dummy, root)
        leaf2 = Node.ensure_ancestry_to(dummy, root)
        self.assertIs(leaf1, leaf2)

    def test_ensure_ancestry_to_changes_leaf_only(self):
        root = self._make_one()
        dummy = _Dummy('/a/b/c', ['Anonymous'])
        Node = self._get_target_class()
        leaf1 = Node.ensure_ancestry_to(dummy, root)
        self.assertFalse(root['a']['b'].block_inherit_roles)
        root['a']['b'].block_inherit_roles = True
        leaf2 = Node.ensure_ancestry_to(dummy, root)
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
        Node = self._get_target_class()
        Node.ensure_ancestry_to(dummy1, root)
        Node.ensure_ancestry_to(dummy2, root)
        descendant_ids = list(node.id for node in root.descendants())
        expected_order = ['a', 'b', 'c1', 'd1', 'e1', 'c2', 'd2', 'e2', 'f2']
        self.assertEqual(descendant_ids, expected_order)

    def test_descendants_deep_with_ignore_block(self):
        root = self._make_one()
        dummy1 = _Dummy('/a/b/c1/d1/e1', ['Anonymous'])
        dummy2 = _Dummy('/a/b/c2/d2/e2/f2', ['Editor'])
        Node = self._get_target_class()
        Node.ensure_ancestry_to(dummy1, root)
        Node.ensure_ancestry_to(dummy2, root)
        root['a']['b']['c2']['d2'].block_inherit_roles = True

        descendants = root.descendants(ignore_block=False)
        descendant_ids = list(node.id for node in descendants)
        expected_order = ['a', 'b', 'c1', 'd1', 'e1', 'c2']
        self.assertEqual(descendant_ids, expected_order)

        descendants = root.descendants(ignore_block=True)
        descendant_ids = list(node.id for node in descendants)
        expected_order = ['a', 'b', 'c1', 'd1', 'e1', 'c2', 'd2', 'e2', 'f2']
        self.assertEqual(descendant_ids, expected_order)

