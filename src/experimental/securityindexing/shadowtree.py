u"""Manage a shadow tree of nodes maintaining security information.

A shadow tree mirrors the Portal content tree in a Zope/Plone site,
each node storing security identifiers in order to enablable
an index to make decisions when indexing.
"""
import BTrees
from persistent import Persistent
from plone import api
from zope import interface

from .interfaces import IShadowTreeNode


_marker = object()


@interface.implementer(IShadowTreeNode)
class Node(Persistent):
    u"""A Node corresponding to an item in the content tree."""

    __parent__ = None
    u"The parent node"

    id = None
    block_inherit_roles = False
    token = None
    physical_path = None

    def __init__(self, id=b'', parent=None, family=BTrees.family64):
        super(Node, self).__init__()
        self._data = family.OO.BTree()
        self.id = id
        self.__parent__ = parent
        interface.alsoProvides(self, BTrees.Interfaces.IBTree)

    def __repr__(self):  # pragma: no cover
        return b'%s("%s")' % (type(self).__name__, self.id)

    def __getattr__(self, name):
        value = getattr(self._data, name, _marker)
        if value is _marker:
            raise AttributeError(
                b'%r object has no attribute %r' % (
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
        if isinstance(obj, (tuple, list)):
            path_components = obj
        else:
            path_components = obj.getPhysicalPath()
        portal_path_idx = 0
        if portal_id in path_components:
            portal_path_idx = path_components.index(portal_id)
        portal_path_idx += 1
        return tuple(path_components[portal_path_idx:])

    @classmethod
    def create_security_token(cls, obj):
        u"""Create a security token for ``obj``.

        We use the return value of `acl_users._getAllLocalRoles`
        as for hashing, since its desired to use all parent local roles.

        ``allowedRolesUsers`` is not used, as  sometimes the sequence does
        not contain the full set of local roles, since shortcuts are utilised
        for certain cases, e.g:

          * Anonymous
          * Authenticated

        :param obj: The content item.
        :type obj: IContentish
        :returns: The hash of the local role information contained by ``obj``.
        :rtype: int
        """
        acl_users = api.portal.get_tool(name=b'acl_users')
        ac_local_roles = acl_users._getAllLocalRoles(obj)
        local_roles = tuple((k, frozenset(v))
                            for (k, v) in ac_local_roles.items())
        return hash(local_roles)

    @staticmethod
    def get_local_roles_block(obj):
        return getattr(obj, b'__ac_local_roles_block__', False)

    def ensure_ancestry_to(self, obj):
        u"""Retrieve the shadow node for corresponding content object.

        Ensures that a corresponding shadow node exists for each ancestor
        of ``obj.getPhysicalPath()``.

        :param obj: The content object.
        :type obj: Products.CMFCore.PortalContent
        :returns: The node correspoinding to the tail
                  component of ``obj.getPhysicalPath()``.
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
        node.physical_path = obj.getPhysicalPath()
        return node

    def update_security_info(self, obj):
        u"""Update the security information for an object.

        :param obj: The portal content object.
        :type obj: Products.CMFCore.PortalContent
        """
        self.physical_path = obj.getPhysicalPath()
        self.block_inherit_roles = self.get_local_roles_block(obj)
        self.token = self.create_security_token(obj)

    def descendants(self, ignore_block=False):
        u"""Generates descendant nodes.

        Optionally yields nodes that have local roles blocked.

        :param ignore_block: If False and a node has block_local_roles setpl
                             to True, do not descend to any of its children.
        """
        for node in self.values():
            if node.block_inherit_roles and not ignore_block:
                break
            yield node
            for descendant in node.descendants(ignore_block=ignore_block):
                yield descendant

    def traverse(self, traversable):
        """Traverse to a node for the given traversable object.

        :param obj: A traversable.
        :type obj: str, tuple, list
        :returns: The node found for the given path.
        :rtype: experimental.securityindexing.shadowtree.Node
        :raises: LookupError
        """
        if isinstance(traversable, (list, tuple)):
            physical_path = traversable
        elif isinstance(traversable, basestring):
            physical_path = tuple(traversable.split(b'/'))
        else:
            raise TypeError(b'Object %r is not traversable' % traversable)
        if physical_path[0] != self.id:
            raise LookupError(
                b'Cannot traverse from here %r '
                b'to  a node from that path %r.' % (self.id, physical_path)
            )
        node = self
        for comp in self._get_path_components(physical_path):
            if comp in node:
                node = node[comp]
            else:
                raise LookupError(physical_path)
        return node
