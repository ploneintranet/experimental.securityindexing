import BTrees
import zope.interface


class IObjectSecurity(zope.interface.Interface):
    """Defines a efficient re-indexing operation."""

    def reindex():
        """Reindex object security."""


class IShadowTree(BTrees.Interfaces.IMinimalDictionary):
    """Marker."""
