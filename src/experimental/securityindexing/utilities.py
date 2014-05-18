from plone import api
from zope import interface
from zope.annotation.interfaces import IAnnotations

from . import shadowtree
from .interfaces import IShadowTreeRoot, IShadowTreeTool


@interface.implementer(IShadowTreeTool)
class ShadowTreeTool(object):

    _pkey = __package__

    @staticmethod
    def _get_storage(portal=None):
        if portal is None:
            portal = api.portal.get()
        return IAnnotations(portal)

    @classmethod
    def delete_from_storage(cls, portal):
        u"""Delete the shadownode tree from persistent storage.

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
