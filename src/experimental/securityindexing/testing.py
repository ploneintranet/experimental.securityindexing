from importlib import import_module

import plone.api as api
import plone.app.testing as pa_testing

from .interfaces import IShadowTreeTool


_marker = object()


class SecurityIndexingLayer(pa_testing.PloneWithPackageLayer):

    def __init__(self, bases=(), name=None):
        init = super(SecurityIndexingLayer, self).__init__
        if bases is ():
            bases = (pa_testing.PLONE_FIXTURE,)
        if name is None:
            name = type(self).__name__
        init(bases=bases,
             name=name,
             zcml_filename=b'configure.zcml',
             zcml_package=import_module(__package__),
             additional_z2_products=(__package__,),
             gs_profile_id=b'%s:default' % (__package__,))

    def tearDownZope(self, app):
        # This does not call Extensions.Install.uninstall for some reason?
        # z2.uninstallProduct(app, __package__)
        qi_tool = app.plone.portal_quickinstaller
        qi_tool.uninstallProducts([__package__])
        assert not qi_tool.isProductInstalled(__package__), (
            b'Yikes!'
            b'Probably an improt error in Extensions/Install.py '
            b'since Zope2 loads this in an Extension method '
            b'not importing the module in the normal Python context.'
        )

    def tearDownPloneSite(self, portal):
        self.applyProfile(portal, b'%s:uninstall' % (__package__,))


FIXTURE = SecurityIndexingLayer()

INTEGRATION = pa_testing.IntegrationTesting(
    bases=(FIXTURE,),
    name=b'SecurityIndexingLayer:Integration'
)


class TestCaseMixin(object):
    """Base mixin class for unittest.TestCase."""

    def _set_default_workflow_chain(self, workflow_id):
        wftool = api.portal.get_tool(b'portal_workflow')
        wftool.setDefaultChain(workflow_id)

    def _create_folder(self, path, local_roles,
                       userid=pa_testing.TEST_USER_ID,
                       block=_marker):
        id = path.split('/')[-1]
        parent_path = filter(bool, path.split('/')[:-1])
        if parent_path:
            obj_path = b'/%s' % '/'.join(parent_path)
            parent = api.content.get(path=obj_path)
        else:
            parent = self.portal
        folder = api.content.create(container=parent,
                                    type=b'Folder',
                                    id=id)
        api.user.grant_roles(username=userid,
                             obj=folder,
                             roles=local_roles)
        if block is not _marker:
            folder.__ac_local_roles_block__ = block
        self._call_mut(folder)
        self.folders_by_path[path] = folder

    def _get_shadowtree_root(self):
        portal = api.portal.get()
        st = portal.getSiteManager().getUtility(IShadowTreeTool)
        return st.root

    def _check_paths_equal(self, paths, expected_paths):
        self.assertSetEqual(paths, set(expected_paths))

    def _check_shadowtree_paths(self, root, expected_paths):
        shadow_paths = {
            node.physical_path
            for node in root.descendants(ignore_block=True)
        }
        # exclude folders created by other fixtures (p.a.event in this case)
        # shadow_paths.remove(('', 'plone', 'robot-test-folder'))
        self._check_paths_equal(shadow_paths, expected_paths)

    def _check_shadowtree_nodes_have_security_info(self):
        portal_id = self.portal.getId()
        for (path, obj) in sorted(self.folders_by_path.items(), key=len):
            path_components = list(filter(bool, obj.getPhysicalPath()))
            path_components.remove(portal_id)
            node = self._get_shadowtree_root()
            for path_component in path_components:
                node = node[path_component]
                self.assertTrue(hasattr(node, b'block_inherit_roles'))
                self.assertTrue(node.token,
                                msg=b'Node has no security info: %r' % (node,))
            self.assertEqual(node.physical_path, obj.getPhysicalPath())

    def _create_members(self, member_ids):
        for member_id in member_ids:
            email = b'%s@plone.org' % (member_id,)
            api.user.create(username=member_id, email=email)

    def _check_shadowtree_integrity(self):
        st_root = self._get_shadowtree_root()
        root_path = b'/' + self.portal.getId()
        indexed_paths = {
            tuple(brain.getPath().split(b'/'))
            for brain in self.catalog.unrestrictedSearchResults(path=root_path)
        }
        self._check_shadowtree_paths(st_root, indexed_paths)

    @property
    def portal(self):
        return self.layer[b'portal']

    @property
    def catalog(self):
        return api.portal.get_tool(b'portal_catalog')

    def setUp(self):
        self.folders_by_path = {}
