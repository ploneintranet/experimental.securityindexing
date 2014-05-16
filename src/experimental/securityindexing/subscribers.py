from Products.CMFCore.interfaces import IContentish
from five import grok
from plone import api
from zope.lifecycleevent.interfaces import (
    IObjectAddedEvent, IObjectRemovedEvent
)

from .interfaces import IShadowTree


def _shadowtree_node_for_content(obj):
    # shadowtree = component.getUtility(IShadowTre e)
    portal = api.portal.get()
    site = portal.getSiteManager()
    shadowtree = site.getUtility(IShadowTree)
    root = shadowtree.root
    node = root.ensure_ancestry_to(obj)
    return node


@grok.subscribe(IContentish, IObjectAddedEvent)
def on_object_added(obj, event):
    node = _shadowtree_node_for_content(obj)
    node.update_security_info(obj)
    assert node.physical_path == obj.getPhysicalPath()


@grok.subscribe(IContentish, IObjectRemovedEvent)
def on_object_removed(obj, event):
    node = _shadowtree_node_for_content(obj)
    parent = node.__parent__
    if parent is not None and obj.getId() in parent:
        del parent[obj.getId()]
