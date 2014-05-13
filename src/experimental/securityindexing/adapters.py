# import zope.component
# import zope.interface
# from Products.CMFCore.interfaces import ICatalogAware, IContentish


# @zope.interface.implementer(ICatalogAware)
# @zope.component.adapter(IContentish, ICatalogAware)


class ARUIndexer(object):

    def __init__(self, context, catalog_tool):
        self.context = context
        self.catalog_tool = catalog_tool

    def __getattr__(self, name):
        return getattr(self.context, name)

    def reindexObjectSecurity(self, obj, skip_self=False):
        # self.catalog_tool.catalog_object(obj, idxs=('allowedRolesAndUsers',),)
        raise NotImplementedError('TODO')
