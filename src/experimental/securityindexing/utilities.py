from collections import namedtuple

from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem
from Products.CMFCore.permissions import ManagePortal
from plone import api
from zope import component, interface
from zope.annotation.interfaces import IAnnotations

from . import shadowtree
from .interfaces import IObjectSecurity, IShadowTreeRoot, IShadowTreeTool


_IntegityInfo = namedtuple(b'IntegrityInfo', (
    b'catalog_paths',
    b'n_cataloged',
    b'shadowtree_paths',
    b'n_shadowed'
))


class IntegrityInfo(_IntegityInfo):

    def is_integral(self):
        return self.n_cataloged == self.n_shadowed


@interface.implementer(IShadowTreeTool)
class ShadowTreeTool(SimpleItem):
    b"""Maintains a shadowtree of hints for controlling
    object security indexing operations.
    """

    _pkey = __package__
    _synchronised = False
    title = __doc__.strip().rstrip(b'.')

    security = ClassSecurityInfo()
    security.declarePrivate(ManagePortal, b'delete_from_storage')
    security.declarePrivate(ManagePortal, b'integrity_info')
    security.declarePrivate(ManagePortal, b'sync')

    @staticmethod
    def _get_storage(portal=None):
        if portal is None:
            portal = api.portal.get()
        return IAnnotations(portal)

    @classmethod
    def delete_from_storage(cls, portal):
        u"""Delete the shadow tree from persistent storage.

        :param portal: The Plone site portal object.
        """
        storage = cls._get_storage(portal=portal)
        if cls._pkey in storage:
            del storage[cls._pkey]

    def integrity_info(self):
        root = self.root
        descendants = list(root.descendants(ignore_block=True))
        path = api.portal.get().getPhysicalPath()
        catalog = api.portal.get_tool(name=b'portal_catalog')
        brains = catalog.unrestrictedSearchResults(path=path)
        catalog_paths = {brain.getPath() for brain in brains}
        shadowtree_paths = {
            b'/'.join(node.physical_path)
            for node in descendants
            if node.physical_path is not None
        }
        info = IntegrityInfo(catalog_paths=catalog_paths,
                             n_cataloged=len(brains),
                             shadowtree_paths=shadowtree_paths,
                             n_shadowed=len(shadowtree_paths))
        return info

    @property
    def root(self):
        u"""Lazily return the root node if it's not yet been created."""
        storage = self._get_storage()
        root_node = storage.setdefault(self._pkey, shadowtree.Node())
        interface.alsoProvides(root_node, IShadowTreeRoot)
        return root_node

    def sync(self, catalog):  # pragma: no cover
        u"""Synchronise security info of site content into the shadow tree.

        This method may be expensive dependant upon the site of the site.

        :param catalog: The catalog to obtain content from.
        """
        root = self.root
        brains = catalog.unrestrictedSearchResults(path=b'/')
        for brain in brains:
            obj = brain.getObject()
            node = root.ensure_ancestry_to(obj)
            obj_sec = component.getMultiAdapter((obj, catalog),
                                                IObjectSecurity)
            obj_sec.reindex_object(obj)
            node.update_security_info(obj)
