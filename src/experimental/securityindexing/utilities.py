from plone import api
from zope import interface
from zope.annotation.interfaces import IAnnotations

from . import shadowtree
from .interfaces import IShadowTreeTool


@interface.implementer(IShadowTreeTool)
class ShadowTreeTool(object):

    def __init__(self):
        self._root = None

    def _get_storage(self):
        return IAnnotations(api.portal.get())

    @property
    def root(self):
        if self._root is None:
            storage = self._get_storage()
            self._root = shadowtree.Node()
            storage[__package__] = self._root
        return self._root
