import plone.api as api

from .interfaces import IShadowTreeTool


_marker_name = b'experimental.securityindexing-various.txt'


def import_various(context):
    if context.readDataFile(_marker_name) is None:
        return
    portal = context.getSite()
    sm = portal.getSiteManager()
    catalog = api.portal.get_tool(name=b'portal_catalog')
    sm.getUtility(IShadowTreeTool).sync(catalog)
