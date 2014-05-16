from .. import shadowtree


def uninstall(portal, reinstall=False):
    if not reinstall:
        shadowtree.destroy()
