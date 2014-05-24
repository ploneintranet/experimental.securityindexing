from plone import api
from zope import component, interface
from zope.annotation.interfaces import IAnnotations

from . import shadowtree
from .interfaces import IObjectSecurity, IShadowTreeRoot, IShadowTreeTool


@interface.implementer(IShadowTreeTool)
class ShadowTreeTool(object):
    u"""A tool to provide access to the ``shadow tree``."""

    _pkey = __package__

    @staticmethod
    def _get_storage(portal=None):
        if portal is None:
            portal = api.portal.get()
        return IAnnotations(portal)

    @classmethod
    def delete_from_storage(cls, portal):
        u"""Delete the shadow tree from persistent storage.

        :param portal: The Plone site portal object.
        """
        storage = cls._get_storage(portal=portal)
        if cls._pkey in storage:
            del storage[cls._pkey]

    @property
    def root(self):
        u"""Lazily return the root node if it's not yet been created."""
        storage = self._get_storage()
        root_node = storage.setdefault(self._pkey, shadowtree.Node())
        interface.alsoProvides(root_node, IShadowTreeRoot)
        return root_node

    def sync(self, catalog):
        root = self.root
        for brain in catalog.unrestrictedSearchResults(path=b'/'):
            brain_path = brain.getPath()
            try:
                root.traverse(brain_path)
            except LookupError:
                obj = brain.getObject()
                node = root.ensure_ancestry_to(obj)
                obj_sec = component.getMultiAdapter((obj, catalog),
                                                    IObjectSecurity)
                obj_sec._reindex_object(obj)
                node.update_security_info(obj)
