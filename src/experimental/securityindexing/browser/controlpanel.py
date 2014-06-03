from Products.CMFPlone.PloneBatch import Batch
from Products.Five import BrowserView
from plone import api
from zope import component

from ..interfaces import IShadowTreeTool
from .. import _


class ControlPanel(BrowserView):

    _tool = None
    info = None
    label = _(u'Experimental Security Indexing')
    description = _(u'Shows the synchronisation status of the '
                    u'internal shadow tree')

    def __call__(self):
        if self.request.method == 'POST':
            return self.handle_sync()
        form = self.request.form
        b_start = int(form.get(b'b_start', '0'))
        self.update()
        self.rows = []
        info = self.info
        if info.catalog_paths.symmetric_difference(info.shadowtree_paths):
            all_paths = info.catalog_paths.union(info.shadowtree_paths)
            paths = filter(bool, all_paths)
            visual_truth = {True: u'\u2714', False: u'\u2717'}
            for path in sorted(paths, key=len):
                in_catalog = path in info.catalog_paths
                in_shadowtree = path in info.shadowtree_paths
                if in_catalog and in_shadowtree:  # pragma: no cover
                    continue
                self.rows.append({
                    b'path': path,
                    b'allowedRolesAndUsers index': visual_truth[in_catalog],
                    b'shadowtree': visual_truth[in_shadowtree]
                })
        self.rows = Batch(self.rows, 10, b_start, orphan=1)
        return self.index()

    @property
    def action(self):
        return self.request.getURL()

    def available(self):
        return not self.info.is_integral()

    def getContent(self):
        return dict(rows=self.rows, info=self.info)

    def update(self):
        st = component.getUtility(IShadowTreeTool)
        self.info = st.integrity_info()

    def handle_sync(self):
        catalog = api.portal.get_tool(name=b'portal_catalog')
        shadowtree = component.getUtility(IShadowTreeTool)
        shadowtree.sync(catalog)
        api.portal.show_message(message=u'Synchronisation complete',
                                type=b'info',
                                request=self.request)
        return self.request.response.redirect(self.action)
