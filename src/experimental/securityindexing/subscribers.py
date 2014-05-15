from __future__ import print_function

from Products.CMFCore.interfaces import IContentish, IIndexableObject
from five import grok
from plone import api
from zope.component import queryMultiAdapter
from zope.lifecycleevent.interfaces import (
    IObjectAddedEvent,
    IObjectRemovedEvent
)

from . import shadowtree


@grok.subscribe(IContentish, IObjectAddedEvent)
def on_object_added(obj, event):
    # TODO: this may be too naive for AT
    #       probably want to do the thing for each catalog
    #       like Products.Archetypes.CatalogMultiplex.reindexObjectSecurity
    catalog = api.portal.get_tool('portal_catalog')
    indexable = queryMultiAdapter((obj, catalog), IIndexableObject)
    if indexable is not None:
        root = shadowtree.get_root()
        node = root.ensure_ancestry_to(obj)
        node.update_security_info(indexable)
        assert node.physical_path == obj.getPhysicalPath()


@grok.subscribe(IContentish, IObjectRemovedEvent)
def on_object_removed(obj, event):
    root = shadowtree.get_root()
    node = root.ensure_ancestry_to(obj)
    parent = node.__parent__
    if parent is not None and obj.getId() in parent:
        del parent[obj.getId()]
