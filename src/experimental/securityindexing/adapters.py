import collections

from Products.CMFCore.interfaces import IIndexableObject
from zope.component import getMultiAdapter

from . import shadowtree


class _IndexablContentProxy(object):

    def __init__(self, aru, node):
        self._aru = aru
        self._id = node.id
        self._path_components = node.physical_path

    def allowedRolesAndUsers(self):
        return self._aru

    def getId(self):
        return self._id

    def getPhysicalPath(self):
        return self._path_components


class ARUIndexer(object):

    def __init__(self, context, catalog_tool):
        self.context = context
        self.catalog_tool = catalog_tool
        self._shadowtree = shadowtree.get_root()

    def __getattr__(self, name):
        return getattr(self.context, name)

    def _reindex_object_security(self, obj):
        path = obj.getPath()
        idxs = self.context._cmf_security_indexes
        reindex = self.catalog_tool.reindexObject
        reindex(obj, idxs=idxs, update_metadata=0, uid=path)

    def _to_indexable(self, obj):
        return getMultiAdapter((obj, self.catalog_tool), IIndexableObject)

    def reindexObjectSecurity(self, skip_self=False):
        obj = self.context
        shared_tokens = collections.defaultdict(list)
        node = self._shadowtree.ensure_ancestry_to(obj)
        shared_tokens[node.token].append(node)
        node.update_security_info(self._to_indexable(obj))
        for descendant in node.descendants():
            shared_tokens[descendant.token].append(descendant)
        traverse = self.context.unrestrictedTraverse
        reindex_object = self.catalog_tool.reindexObject
        unindex_object = self.catalog_tool.unindexObject
        for (old_token, nodes_group) in shared_tokens.items():
            first_node = next(iter(nodes_group))
            first_path = '/'.join(first_node.physical_path)
            first_obj = traverse(first_path)
            indexable = self._to_indexable(first_obj)
            aru = indexable.allowedRolesAndUsers
            for node in nodes_group:
                content_proxy = _IndexablContentProxy(aru, node)
                unindex_object(content_proxy)
                reindex_object(content_proxy)
