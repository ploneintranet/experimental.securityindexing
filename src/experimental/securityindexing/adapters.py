"""Provide an 'adapter' which implements `reindexObjectSecurity`.

The goal is to improve the efficiency of the pre-existing
`reindexObjectSecurity`:

  * Products.CMFCore.CMFCatalogAware.CatalogAware

  * Products.Archetypes.CatalogMultiplex.CatalogMultiplex

which both re-index the current context and *all* of
the descendant nodes of the current context with the
content tree.


The basic idea here, is to fetch as few objects from the ZODB as
possible, and only re-index descendant nodes that have changed
with respect to the current context.

This involves consideration of:

    * __ac_local_roles_block__:

        If set to a 'truthy' value, then any node and it's descendants
        will be not be indexed.

    * acl_users._getAllLocalRoles (
        combined __ac__local_roles__ when inheriting of local roles is 'on'
      ):

        Nodes which share the same local roles as the current context
        do not need to be re-indexed.

        Group descendant nodes by a shared token (hash) of their
        respective (location aware combination) local roles.
        We index a faux object representing the content object
        for each object in the group, having fetched only one from the ZODB,
        with the knowledge that the `allowedRolesAndUsers` value will be the
        same for each.

The algorithm implement here for `reindexObjectSecurity`
is as follows:

 1. Record the security token (hashed  value of all local roles)
    before and after re-indexing the current context.

TODO: if skip_self is True, we should not re-index ourselves,
      but then what to do about descendants? [1]

 TODO: revise (2.) with respect to the above TODO [1]
 2. Re-index our context, as we need to do this regardless of changes
    as this might have been a workflow change, and hence
    allowedRolesAndUsers may have changed.

 3. Re-index descendants as local roles may have changed,
    implying the value of allowedRolesAndUsers has also changed.
    Note that we never fetch descendants 'lower' than the parent
    of a node that has '__ac_local_roles_block__' set to a 'Truthy'
    value.

 4. Process the nodes that have the same token, such that we
    avoid retrieving each descendant from the ZODB.

 5. Fetch only the first node from each group of descendants
    which contain the same set of local roles.


Considerations
--------------

   * Users can be assigned 'global' roles

   * Users can be assigned 'local' roles (specific to item of content)

   * Items of content can have a set of allowed roles and users set upon them
     (__ac_local_roles__)

   * Items of content inherit their local roles from the parent container

     * This can be optionally disabled (if __ac_local_roles_block__ is True)

   * Items of content are indexed into a ZCatalog.

   * When a user performs a search, `Products.CMFPlone` calculates which
     items of contents the current user can see, based upon the
     combination of:

     * Global roles assigned to the user

     * Local roles assigned to the user for a given object
       in the content tree (ZODB)

   * A workflow transition can cause the `allowedRolesAndUsers`
     for a given contentish item have `virtual roles` such as
     ['Anonymous'] and ['Authenticated'], which mask the actual roles.
     (e.g The 'show' transition in the default `plone_workflow`
     causes the `allowedRolesAndUsers` to be ['Anonymous'] such that everyone
     can see the item.

   * All `users` will have the role 'Anonymous'

   * All logged-in users will have the roles:
        ['Member', 'Authenticated' and 'Anonymous']
     by default.

"""
import collections

from Products.CMFCore.interfaces import IIndexableObject
from zope.component import getMultiAdapter

from . import shadowtree


class _IndexableContentishProxy(object):
    """A lightweight 'proxy' object.

    This is stand-in for an item of content,
    which implements the bare minimum functionality
    in order for ZCatalog to be able to index
    the `allowedRolesAndUsers` value.
    """

    def __init__(self, aru, node):
        self._aru = aru
        self._path_components = node.physical_path

    def allowedRolesAndUsers(self):
        return self._aru

    def getPhysicalPath(self):
        return self._path_components


class ObjectSecurity(object):
    """Manage reindexing object security of the `allowedRolesAndUsers` index.
    """

    _index_ids = ('allowedRolesAndUsers',)

    def __init__(self, context, catalog_tool):
        self.context = context
        self.catalog_tool = catalog_tool
        self._shadowtree = shadowtree.get_root()

    def _reindex_object(self, obj):
        reindex = self.catalog_tool.reindexObject
        reindex(obj, idxs=self._index_ids, update_metadata=0)

    def _to_indexable(self, obj):
        return getMultiAdapter((obj, self.catalog_tool), IIndexableObject)

    def reindex(self, skip_self=False):
        """Reindex the contents of `allowedRolesAndUsers` index.

        Potentially reindex descendant objects in the content tree.

        This method utilises a `shadow tree` which has the same structure
        as the content tree, containing minimal information such that
        this method can make descisions regarding which descendants need
        to be re-indexed.
        """
        node = self._shadowtree.ensure_ancestry_to(self.context)
        token_before = node.token
        # TODO: if skip_self is True, we should not reindex ourselfs,
        #       but then what to do about descendants?
        self._reindex_object(self.context)
        node.update_security_info(self.context)
        token_after = node.token
        if token_before != token_after:
            shared_tokens = collections.defaultdict(list)
            shared_tokens[node.token].append(node)

            for descendant in node.descendants(ignore_block=False):
                shared_tokens[descendant.token].append(descendant)

            traverse = self.context.unrestrictedTraverse
            for (old_token, nodes_group) in shared_tokens.items():
                first_node = next(iter(nodes_group))
                first_path = '/'.join(first_node.physical_path)
                first_obj = traverse(first_path)
                indexable = self._to_indexable(first_obj)
                aru = indexable.allowedRolesAndUsers
                for node in nodes_group:
                    content_proxy = _IndexableContentishProxy(aru, node)
                    self._reindex_object(content_proxy)
