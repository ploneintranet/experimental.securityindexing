from plone import api
from zope import interface

from . import shadowtree
from .interfaces import IShadowTree


@interface.implementer(IShadowTree)
class ShadowTree(object):

    def __init__(self):
        self._root = None

    @property
    def root(self):
        if self._root is None:
            portal = api.portal.get()
            self._root = shadowtree.Node.create_root(context=portal)
        return self._root

    def delete_root(self, portal):
        shadowtree.Node.delete_root(context=portal)
