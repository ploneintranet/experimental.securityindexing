"""Manage a shadow tree of nodes maintaining security information.

A shadow tree mirrors the Portal content tree in a Zope/Plone site,
each node storing security identifiers in order to enablable
an index to make decisions when indexing.
"""
from __future__ import print_function

import BTrees
import zope.interface
from persistent import Persistent
from plone import api
from zope.annotation.interfaces import IAnnotations


_marker = object()


def _get_storage():
    return IAnnotations(api.portal.get())


def destroy():
    storage = _get_storage()
    if __package__ in storage:
        del storage[__package__]


def get_root():
    """Gets the root shadow tree.

    Creates the root node if one hasn't previously been
    created.
    """
    # TODO: This annotated storage needs to be deleted upon product uninstall
    #       We'll need to split this function up in order
    #       to clear the shadow tree in the GS uninstall profile.
    storage = _get_storage()
    root = storage.get(__package__)
    if root is None:
        root = Node()
        storage[__package__] = root
    return root


@zope.interface.implementer(BTrees.Interfaces.IDictionaryIsh)
class Node(Persistent):
    """A Node corresponding to a content item in the a Zope instance.
    """
    __parent__ = None
    id = None
    block_inherit_roles = False
    token = None
    physical_path = None
    family = BTrees.family64

    def __init__(self, id='', parent=None):
        super(Node, self).__init__()
        self._data = self.family.OO.BTree()
        self.id = id
        self.__parent__ = parent

    def __repr__(self):  # pragma: no cover
        return '%s("%s")' % (type(self).__name__, self.id)

    def __getattr__(self, name):
        value = getattr(self._data, name, _marker)
        if value is _marker:
            raise AttributeError(
                '%r object has no attribute %r' % (
                    '%s.%s' % (__package__, type(self).__name__),
                    name
                )
            )
        return value

    def __contains__(self, key):
        return key in self._data

    def __setitem__(self, name, value):
        self._data[name] = value

    def __getitem__(self, name):
        return self._data[name]

    def __delitem__(self, name):
        del self._data[name]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __bool__(self):
        return True

    __nonzero__ = __bool__

    @staticmethod
    def _get_path_components(obj):
        portal_id = api.portal.get().getId()
        path_components = obj.getPhysicalPath()
        portal_path_idx = path_components.index(portal_id) + 1
        return tuple(path_components[portal_path_idx:])

    @classmethod
    def create_security_token(cls, obj):
        """Create a security token for `obj`.

        We use the return value of `acl_users._getAllLocalRoles`
        as for hashing, since its desired to use all parent local roles.

        `allowedRolesUsers` is not used, as  sometimes the sequence does
        not contain the full set of local roles, since shortcuts are utilised
        for certain cases, e.g:

          * Anonymous
          * Authenticated

        :param cls: The type of this node.
        :type cls: experimental.localrolesindex.shadowtree.Node
        :param obj: The content item.
        :type obj: IContentish
        :returns: The hash of the local role information contained by `obj`.
        :rtype: int
        """
        acl_users = api.portal.get_tool('acl_users')
        ac_local_roles = acl_users._getAllLocalRoles(obj)
        local_roles = tuple((k, frozenset(v))
                            for (k, v) in ac_local_roles.items())
        return hash(local_roles)

    @staticmethod
    def get_local_roles_block(obj):
        return getattr(obj, '__ac_local_roles_block__', False)

    def ensure_ancestry_to(self, obj):
        """Retrieve the shadow node for corresponding content object.

        Ensures that a corresponding shadow node exists for each ancestor
        of `obj.getPhysicalPath()`.

        :param obj: The content object.
        :type obj: Products.CMFCore.PortalContent
        :returns: The node correspoinding to the tail
                  component of `obj.getPhysicalPath()`
        :rtype: experimental.localrolesindex.shadowtree.Node
        """
        node = self
        cls = type(self)
        for comp in self._get_path_components(obj):
            if comp not in node:
                parent = node
                node = cls(parent=parent, id=comp)
                parent[node.id] = node
            else:
                node = node[comp]
        return node

    def update_security_info(self, obj):
        """Update the security information for an object.

        :param obj: The portal content object.
        :type obj: Products.CMFCore.PortalContent
        """
        self.physical_path = obj.getPhysicalPath()
        self.block_inherit_roles = self.get_local_roles_block(obj)
        self.token = self.create_security_token(obj)
        assert self.id == obj.getId()

    def descendants(self, ignore_block=False):
        """Generates descendant nodes.

        Optionally yields nodes that have local roles blocked.

        :param ignore_block: If False and a node has block_local_roles set
                             to True, do not descend to any of its children.
        """
        for node in self.values():
            if node.block_inherit_roles and not ignore_block:
                break
            yield node
            for descendant in node.descendants(ignore_block=ignore_block):
                yield descendant
