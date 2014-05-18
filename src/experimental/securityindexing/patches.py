from Products.Archetypes.config import TOOL_NAME
from Products.Archetypes.utils import isFactoryContained
from Products.CMFCore.interfaces import ICatalogTool
from Products.CMFCore.utils import getToolByName

from .adapters import ObjectSecurity


def at_reindexObjectSecurity(self):
    if isFactoryContained(self):  # pragma: no cover
        return
    at = getToolByName(self, TOOL_NAME, None)
    if at is None:  # pragma: no cover
        return
    catalogs = [c for c in at.getCatalogsByType(self.meta_type)
                if ICatalogTool.providedBy(c)]
    for catalog in catalogs:
        adapter = ObjectSecurity(self, catalog)
        adapter.reindex()


def dx_reindexObjectSecurity(self):
    catalog_tool = self._getCatalogTool()
    if catalog_tool is None:  # pragma: no cover
        return
    adapter = ObjectSecurity(self, catalog_tool)
    adapter.reindex()
