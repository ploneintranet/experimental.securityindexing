# import plone.api as api

# from .interfaces import IShadowTreeTool


# _marker_name = b'experimental.securityindexing-various.txt'


# def import_various(context):
#     if context.readDataFile(_marker_name) is None:
#         return
#     catalog = api.portal.get_tool(name=b'portal_catalog')
#     portal = context.getSite()
#     sm = portal.getSiteManager()
#     st_tool = sm.getUtility(IShadowTreeTool)
#     st_tool.sync_all_content(catalog)
