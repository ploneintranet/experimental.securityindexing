import zope.interface


class IARUIndexer(zope.interface.Interface):

    def reindexObjectSecurity(obj, skip_self=False):
        """Reindex object security."""
