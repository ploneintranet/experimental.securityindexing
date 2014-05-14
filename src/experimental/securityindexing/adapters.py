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

    _index_ids = ('allowedRolesAndUsers',)

    def __init__(self, context, catalog_tool):
        self.context = context
        self.catalog_tool = catalog_tool
        self._shadowtree = shadowtree.get_root()

    def __getattr__(self, name):
        return getattr(self.context, name)

    def _reindex_object_security(self, obj):
        reindex = self.catalog_tool.reindexObject
        reindex(obj, idxs=self._index_ids, update_metadata=0)

    def _to_indexable(self, obj):
        return getMultiAdapter((obj, self.catalog_tool), IIndexableObject)

    def reindexObjectSecurity(self, skip_self=False):
        obj = self.context
        # Get this object's corresponding node in the
        # shadow tree, ensuring we have all intermediate nodes
        # on the path to it
        node = self._shadowtree.ensure_ancestry_to(obj)
        # We need to get the has value of before the node is
        # updated in order to determine what needs to be done later
        token_before = node.token
        # Update the security info, which will potentially change
        # the hash value due to local roles
        node.update_security_info(obj)
        # Get the token afterwards
        token_after = node.token

        # reindex ourself, as we need to do this regardless of changes
        # as this might have been a workflow change, and hence
        # allowedRolesAndUsers may have changed.
        self._reindex_object_security(obj)

        if token_before != token_after:
            # The tokens before and after are different which means
            # we need to re-index our children as our local roles
            # have changed, and hence the value of allowedRolesAndUsers
            # We need to group the nodes that have the same token
            # we start with adding overself.
            shared_tokens = collections.defaultdict(list)
            shared_tokens[node.token].append(node)
            # We get all our descendants, that inherit local roles from us
            # ie we stop at local role blocks as there is no change we
            # could have done that would affect their allowedRolesAndUsers
            # value
            for descendant in node.descendants():
                shared_tokens[descendant.token].append(descendant)
            traverse = self.context.unrestrictedTraverse
            # For each group of nodes with the same token...
            for (old_token, nodes_group) in shared_tokens.items():
                # get the first node of the group and get its
                # corresponding object from the content tree
                first_node = next(iter(nodes_group))
                first_path = '/'.join(first_node.physical_path)
                first_obj = traverse(first_path)
                # We need to manually adapt this object so that
                # we have the allowedRolesAndUsers attribute on it
                indexable = self._to_indexable(first_obj)
                aru = indexable.allowedRolesAndUsers
                # For each of the nodes in the group...
                for node in nodes_group:
                    # create a lightweight 'proxy' object that just has
                    # enough information to keep the catalog happy
                    content_proxy = _IndexablContentProxy(aru, node)
                    # Reindex the proxy object
                    self._reindex_object_security(content_proxy)
