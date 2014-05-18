from importlib import import_module

from plone.app.contenttypes.testing import PLONE_APP_CONTENTTYPES_FIXTURE
import plone.api as api
import plone.app.testing as pa_testing

from .interfaces import IShadowTreeTool


_marker = object()


class SecurityIndexingBaseLayer(pa_testing.PloneWithPackageLayer):

    @classmethod
    def create(cls, bases, name_suffix):
        name = b'{}()'.format(cls.__name__, name_suffix)
        return cls(
            name=name,
            bases=bases,
            zcml_filename=b'configure.zcml',
            zcml_package=import_module(__package__),
            additional_z2_products=(__package__,),
            gs_profile_id=b'%s:default' % (__package__,)
        )


class SecurityIndexingLayer(SecurityIndexingBaseLayer):

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


AT_FIXTURE = SecurityIndexingLayer.create(
    (pa_testing.PLONE_FIXTURE,),
    b'AT'
)

DX_FIXTURE = SecurityIndexingLayer.create(
    (PLONE_APP_CONTENTTYPES_FIXTURE,),
    b'DX'
)

# [A-Z]{3,3} Prefixing of layer names here
# is done to force ordering of layer executation
# by zope.testrunner, such that p.a.testing does not choke.
# For some reason DemoStorage created by p.testing.z2 goes AWOL
# unless DX tests run first. (p.a.event testing problem?)

AT_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_FIXTURE,),
    name=b'ZZZ_ATLayer:Integration'
)

DX_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_FIXTURE,),
    name=b'YYY_DXLayer:Integration'
)


class TestCaseMixin(object):
    """Base mixin class for unittest.TestCase."""

    def _set_default_workflow_chain(self, workflow_id):
        wftool = api.portal.get_tool('portal_workflow')
        wftool.setDefaultChain(workflow_id)

    def _create_folder(self, path, local_roles,
                       userid=pa_testing.TEST_USER_ID,
                       block=_marker):
        id = path.split('/')[-1]
        parent_path = filter(bool, path.split('/')[:-1])
        if parent_path:
            obj_path = '/%s' % '/'.join(parent_path)
            parent = api.content.get(path=obj_path)
        else:
            parent = self.portal
        folder = api.content.create(container=parent,
                                    type='Folder',
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

    def _check_shadowtree_paths(self, root, expected_paths):
        shadow_paths = {
            node.physical_path
            for node in root.descendants(ignore_block=True)
        }
        # Remove the robot-test-folder created by the
        # p.a.{event,conenttypes} fixture.
        exclude = ('', self.portal.getId(), 'robot-test-folder')
        if exclude in expected_paths:
            expected_paths.remove(exclude)
        # exclude folders created by other fixtures (p.a.event in this case)
        # shadow_paths.remove(('', 'plone', 'robot-test-folder'))
        self.assertSetEqual(shadow_paths, expected_paths)

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
