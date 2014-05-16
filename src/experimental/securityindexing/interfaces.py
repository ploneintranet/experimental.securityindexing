import BTrees
import zope.interface


class IObjectSecurity(zope.interface.Interface):
    """Defines a efficient re-indexing operation."""

    def reindex():
        """Reindex object security."""


class IShadowTree(BTrees.Interfaces.IMinimalDictionary):
    """A shadow tree node."""


class IShadowTreeTool(zope.interface.Interface):

    root = zope.interface.Attribute('The root node of the shadow tree')
