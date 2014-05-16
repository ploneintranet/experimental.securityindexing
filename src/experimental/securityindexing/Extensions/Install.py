from zope import component

from ..interfaces import IShadowTree


def uninstall(portal, reinstall=False):
    if reinstall:
        return
    shadowtree = component.getUtility(IShadowTree)
    shadowtree.delete_root(portal)
