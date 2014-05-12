import unittest

from plone.indexer.interfaces import IIndexableObject
from plone import api
from Products.CMFCore.interfaces import ICatalogTool
import mock
import zope.component
import zope.interface

# from ..interfaces import IDecendantLocalRolesAware
from . import testing


class TestSecutityIndexer(unittest.TestCase):
    """Tests for SecutityIndexer Adapter."""

    layer = testing.FIXTURE

    def __getattr__(self, name):
        try:
            return self.layer[name]
        except KeyError:
            raise AttributeError(name)

    def _create_folder(self, path, local_roles, block=False):
        id = path.split('/')[-1]
        parent_path = path.split('/')[:-1]
        if parent_path:
            parent = api.content.get(path=parent_path)
        else:
            parent = self.portal
        folder = api.content.create(container=parent,
                                    id=id,
                                    type='Folder')
        self.folders_by_path[path] = folder

    def _populate(self):
        self.folders_by_path = {}
        create_folder = self._create_folder
        create_folder('/a', ['Anonymous'])
        create_folder('/a/b', ['Anonymous'])
        create_folder('/a/b/c', ['Anonymous', 'Authenticated'])
        create_folder('/a/b/c/a', ['Anonymous', 'Authenticated'])
        create_folder('/a/b/c/d', ['Anonymous', 'Authenticated'])
        create_folder('/a/b/c/e', ['Anonymous', 'Authenticated'], block=True)
        create_folder('/a/b/c/e/f', ['Authenticated'])
        create_folder('/a/b/c/e/f/g', ['Reviewer'])

    def _get_target_class(self):
        from .adapters import SecutityIndexer
        return SecutityIndexer

    def _make_one(self, *args, **kw):
        cls = self._get_target_class()
        return cls(*args, **kw)

    def _query(self, local_roles, operator='or'):
        catalog = api.portal.get_tool('portal_catalog')
        brains = catalog.searchResults({
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

    def _check_index(self, local_roles, expected, operator='or', dummy=None):
        actual = set(self._query_index(local_roles, operator=operator))
        self.assertEqual(actual, set(expected))
        if dummy:
            self._check_shadowtree_nodes_have_security_info(dummy)

    def _effect_change(self, document_id, obj):
        self._values[document_id] = obj
        self._index.index_object(
            document_id,
            obj
        )

    def test_interfaces(self):
        from Products.PluginIndexes.interfaces import IPluggableIndex
        from Products.PluginIndexes.interfaces import ISortIndex
        from Products.PluginIndexes.interfaces import IUniqueValueIndex
        from zope.interface.verify import verifyClass
        LocalRolesIndex = self._get_target_class()
        verifyClass(IPluggableIndex, LocalRolesIndex)
        verifyClass(ISortIndex, LocalRolesIndex)
        verifyClass(IUniqueValueIndex, LocalRolesIndex)

    def test_index_populated(self):
        self._populate_index()
        values = self._values
        self.assertEqual(len(self._index.referencedObjects()), len(values))

    def test_index_clear(self):
        self._populate_index()
        values = self._values
        self.assertEqual(len(self._index.referencedObjects()), len(values))
        self._index.clear()
        self.assertEqual(len(self._index.referencedObjects()), 0)
        self.assertEqual(list(self._index.shadowtree.descendants()), [])

    def test_index_object_noop(self):
        self._populate_index()
        try:
            self._index.index_object(999, None)
        except Exception:
            self.fail('Should not raise (see KeywordIndex tests)')

    def test_index_empty(self):
        self.assertEqual(len(self._index), 0)
        assert len(self._index.referencedObjects()) == 0
        self.assertEqual(self._index.numObjects(), 0)
        self.assertIsNone(self._index.getEntryForObject(1234))
        self.assertEqual(self._index.getEntryForObject(1234, self._marker),
                         self._marker)
        self._index.unindex_object(1234)
        assert self._index.hasUniqueValuesFor('allowedRolesAndUsers')
        assert not self._index.hasUniqueValuesFor('notAnIndex')
        assert len(self._index.uniqueValues('allowedRolesAndUsers')) == 0

    def test_index_object(self):
        self._populate_index()
        self._check_index(['Anonymous'], (0, 1, 2, 3, 4, 5))
        self._check_index(['Authenticated'], (2, 3, 4, 5, 6))
        self._check_index(['Member'], ())

    def test__index_object_on_change_no_recurse(self):
        self._populate_index()
        result = self._query_index(['Anonymous', 'Authenticated'],
                                   operator='and')
        self.assertEqual(list(result), [2, 3, 4, 5])
        self._effect_change(
            4,
            Dummy('/a/b/c/d', ['Anonymous', 'Authenticated', 'Editor'])
        )
        self._check_index(['Anonymous', 'Authenticated'],
                          [2, 3, 4, 5],
                          operator='and')
        self._check_index(['Editor'], [4], operator='and')
        self._effect_change(
            2,
            Dummy('/a/b/c', ['Contributor'])
        )
        self._check_index(['Contributor'], {2})
        self._check_index(['Anonymous', 'Authenticated'], {3, 4, 5},
                          operator='and')

    def test__index_object_on_change_recurse(self):
        self._populate_index()
        self._values[2].aru = ['Contributor']
        dummy = self._values[2]
        zope.interface.alsoProvides(dummy, IDecendantLocalRolesAware)
        self._effect_change(2, dummy)
        self._check_index(['Contributor'], {2, 3, 4}, dummy=dummy)
        self._check_index(['Anonymous', 'Authenticated'],
                          {0, 1, 5, 6},
                          dummy=dummy)

    def test_reindex_no_change(self):
        self._populate_index()
        obj = self._values[7]
        self._effect_change(7, obj)
        self._check_index(['Reviewer'], {7})
        self._effect_change(7, obj)
        self._check_index(['Reviewer'], {7})

    def test_index_object_when_raising_attributeerror(self):
        class FauxObject(Dummy):
            def allowedRolesAndUsers(self):
                raise AttributeError
        to_index = FauxObject('/a/b', ['Role'])
        self._index.index_object(10, to_index)
        self.assertFalse(self._index._unindex.get(10))
        self.assertFalse(self._index.getEntryForObject(10))

    def test_index_object_when_raising_typeeror(self):
        class FauxObject(Dummy):
            def allowedRolesAndUsers(self, name):
                return 'allowedRolesAndUsers'

        to_index = FauxObject('/a/b', ['Role'])
        self._index.index_object(10, to_index)
        self.assertFalse(self._index._unindex.get(10))
        self.assertFalse(self._index.getEntryForObject(10))

    def test_value_removes(self):
        to_index = Dummy('/a/b/c', ['hello'])
        self._index.index_object(10, to_index)
        self.assertIn(10, self._index._unindex)

        to_index = Dummy('/a/b/c', [])
        self._index.index_object(10, to_index)
        self.assertNotIn(10, self._index._unindex)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSecutityIndexer))
    return suite


if __name__ == '__main__':
    unittest.main()
