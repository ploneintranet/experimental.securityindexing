from Products.Archetypes.config import TOOL_NAME
from Products.Archetypes.utils import isFactoryContained
from Products.CMFCore.interfaces import ICatalogTool
from Products.CMFCore.utils import getToolByName

from .adapters import ARUIndexer


def at_reindexObjectSecurity(self, skip_self=False):
    if isFactoryContained(self):
        return
    at = getToolByName(self, TOOL_NAME, None)
    if at is None:
        return
    catalogs = [c for c in at.getCatalogsByType(self.meta_type)
                if ICatalogTool.providedBy(c)]
    for catalog in catalogs:
        adapter = ARUIndexer(self, catalog)
        adapter.reindexObjectSecurity(skip_self=skip_self)


def dx_reindexObjectSecurity(self, skip_self=False):
    catalog_tool = self._getCatalogTool()
    if catalog_tool is None:
        return
    adapter = ARUIndexer(self, catalog_tool)
    adapter.reindexObjectSecurity(skip_self=skip_self)
