from plone import api

from .interfaces import IShadowTreeTool


def _shadowtree_node_for_content(obj):
    portal = api.portal.get()
    site = portal.getSiteManager()
    root = site.getUtility(IShadowTreeTool).root
    return root.ensure_ancestry_to(obj)


def on_object_moved(obj, event):
    u"""Synchronise current security info of ``obj`` to a
    corresponding``shadow tree` node.

    The event should have been configured as a
    ``zope.event.lifecycleevent.IObjectMovedEvent``, which
    is fired upon object creation and deletion in addition
    to when an object is moved or renamed.

    This handler handles creation, moving and renaming.

    :param obj: The content object.
    :param event: The event.
    """
    if event.oldParent and event.newParent:
        old = _shadowtree_node_for_content(event.oldParent)
        del old[event.oldName]
        node = _shadowtree_node_for_content(event.object)
        node.update_security_info(obj)


def on_object_removed(obj, event):
    u"""Synchronise current security info of ``obj`` to a
    corresponding``shadow tree` node.

    :param obj: The content object.
    :param event: The event.
    """
    node = _shadowtree_node_for_content(obj)
    parent = node.__parent__
    if parent is not None and obj.getId() in parent:
        del parent[obj.getId()]
