from zope import interface
from zope.interface.exceptions import Invalid


class IObjectSecurity(interface.Interface):
    u"""Defines a efficient re-indexing operation."""

    context = interface.Attribute(u'The plone content item.')

    catalog_tool = interface.Attribute(u'A plone catalog tool.')

    def reindex():
        u"""Reindex object security."""


class IShadowTreeNode(interface.Interface):
    u"""A shadow tree node."""

    __parent__ = interface.Attribute(u'Parent node.')

    id = interface.Attribute(u'The id of the content item.')

    block_inherit_roles = interface.Attribute(
        u'Recorded value of __ac_local_roles_block__'
    )

    token = interface.Attribute(u'A hash of the local roles of a content item')

    physical_path = interface.Attribute(u'Recorded value of getPhysicalPath()')

    @interface.invariant
    def contained(node):
        if IShadowTreeRoot.providedBy(node):
            return
        if node.__parent__ is None or not node.id:
            raise Invalid(b'A node must be contained within the shadowtree.')

    def create_security_token(obj):
        u"""Create a security token for `obj`.

        We use the return value of `acl_users._getAllLocalRoles`
        as for hashing, since its desired to use all parent local roles.

        `allowedRolesUsers` is not used, as  sometimes the sequence does
        not contain the full set of local roles, since shortcuts are utilised
        for certain cases, e.g:

          * Anonymous
          * Authenticated

        :param obj: The content item.
        :type obj: IContentish
        :returns: The hash of the local role information contained by `obj`.
        :rtype: int
        """

    def descendants(ignore_block=False):
        u"""Generate descendant nodes.

        Optionally yields nodes that have local roles blocked.

        :param ignore_block: If False and a node has block_local_roles setpl
                             to True, do not descend to any of its children.
        """

    def ensure_ancestry_to(obj):
        u"""Retrieve the shadow node for corresponding content object.

        Ensures that a corresponding shadow node exists for each ancestor
        of `obj.getPhysicalPath()`.

        :param obj: The content object.
        :type obj: Products.CMFCore.PortalContent
        :returns: The node correspoinding to the tail
                  component of `obj.getPhysicalPath()`
        :rtype: experimental.localrolesindex.shadowtree.Node
        """

    def get_local_roles_block(obj):
        u"""Get the value of __ac_local_roles_block__ for the node.

        :returns: False if not set, otherwise what ever it was set to.
        :rtype: bool
        """

    def traverse(traversable):
        u"""Traverse to a node for the given traversable object.

        :param obj: A traversable.
        :type obj: str, tuple, list
        :returns: The node found for the given path.
        :rtype: experimental.securityindexing.shadowtree.Node
        :raises: LookupError
        """

    def update_security_info(obj):
        u"""Update the security information for an object.

        :param obj: The portal content object.
        :type obj: Products.CMFCore.PortalContent
        """


class IShadowTreeRoot(IShadowTreeNode):
    u"""Marker."""

    @interface.invariant
    def no_parent(node):
        if node.__parent__ is not None:
            raise Invalid(
                u'Root node of the shadowtree should have no parent'
            )

    @interface.invariant
    def empty_id(node):
        if node.id != b'':
            raise Invalid(
                u'Root node id should be the empty string.'
            )


class IShadowTreeTool(interface.Interface):
    u"""Describes a persistent object by which the shadowtree is obtained."""

    root = interface.Attribute(u'The root node of the shadow tree')

    def delete_from_storage(portal):
        u"""Delete the shadowtree root and all it's data from the portal."""
