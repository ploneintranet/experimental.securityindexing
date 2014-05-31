import collections
import unittest

from zExceptions import Unauthorized
import plone.app.testing as pa_testing
import plone.api as api
import plone.testing.z2 as z2
import transaction

from . import dx
from .. import testing


class ControlPanelTestsMixin(testing.TestCaseMixin):

    def _call_vut(self):
        tool = api.portal.get_tool(name=b'portal_shadowtree')
        view = api.content.get_view(
            context=tool,
            request=self.layer[b'request'],
            name=b'shadowtree-sync')
        assert self.layer[b'request'].method == 'POST', (
            b'Request method was %r' % self.layer[b'request'].method
        )
        view.handle_sync()

    def _populate(self):
        self.folders_by_path.clear()
        st_root = self._get_shadowtree_root()
        st_root.clear()
        create_folder = self._create_folder
        create_folder(b'/a', [b'Reader'], userid=b'matt')
        create_folder(b'/a/b', [b'Reader'])
        create_folder(b'/a/b/c', [b'Reader', b'Editor'])
        create_folder(b'/a/b/c/a', [b'Reader', b'Editor'])
        create_folder(b'/a/b/c/d', [b'Reader', b'Editor'])
        create_folder(b'/a/b/c/e', [b'Reader'], userid=b'liz', block=True)
        create_folder(b'/a/b/c/e/f', [b'Reader'])
        create_folder(b'/a/b/c/e/f/g', [b'Reviewer'])

    def setUp(self):
        super(ControlPanelTestsMixin, self).setUp()
        # Create a user that never is owns
        # any objects created by this test.
        self.query_user = api.user.create(
            email=b'querier-test-user@netsight.co.uk',
            username=b'querier-test-user'
        )
        self._create_members([b'matt', b'liz', b'guido'])
        api.user.grant_roles(username=b'matt', roles=[
            b'Member', b'Contributor', b'Reader', b'Editor'
        ])
        pa_testing.setRoles(self.portal,
                            self.query_user.getUserId(),
                            [b'Manager'])

    def test_handle_sync(self):
        st_root = self._get_shadowtree_root()
        # ensure we have no shadow tree state to start with
        check_shadowtree_integrity = self._check_shadowtree_paths
        check_shadowtree_integrity(st_root, set())

        # create some heirachy of folders, ensure the shadow tree is in sync
        self._populate()

        def check_in_sync():
            root_path = b'{.PLONE_SITE_ID}/a'.format(pa_testing)
            check_shadowtree_integrity(st_root, {
                tuple(b.getPath().split(b'/'))
                for b in self.catalog.unrestrictedSearchResults(path=root_path)
            })

        check_in_sync()

        # clear the shadow tree
        st_root.clear()
        self.assertSetEqual(set(st_root.descendants()), set())

        self.layer[b'request'].method = b'POST'

        # call the handle_sync method of the view
        # and check we are in sync again.
        self._call_vut()
        check_in_sync()


class TestControlPanel(ControlPanelTestsMixin, unittest.TestCase):

    layer = testing.INTEGRATION


class TestControlPanelDDCT(dx.Mixin,
                           ControlPanelTestsMixin,
                           unittest.TestCase):

    layer = dx.INTEGRATION


class TestControlPanelFunctional(ControlPanelTestsMixin, unittest.TestCase):

    layer = testing.FUNCTIONAL

    def _get_uut(self):
        tool = api.portal.get_tool(name=b'portal_shadowtree')
        return tool.absolute_url()

    def _set_credentials(self, username, password):
        key = b'Authorization'
        value = b'Basic %s:%s' % (username, password)
        mech_browser = self.browser.mech_browser
        headers = collections.OrderedDict(mech_browser.addheaders)
        if key in headers:
            del headers[key]
        mech_browser.addheaders = headers.items()
        self.browser.addHeader(key, value)

    def _get_form_after_populate_and_reinstall(self):
        self._populate()
        transaction.commit()
        self._set_credentials(pa_testing.SITE_OWNER_NAME,
                              pa_testing.SITE_OWNER_PASSWORD)
        pkg = __package__.rsplit(b'.', 1)[0]
        QI = api.portal.get_tool(name=b'portal_quickinstaller')
        QI.uninstallProducts([pkg])
        transaction.commit()
        QI.installProducts([pkg])
        transaction.commit()
        self.browser.open(self._get_uut())
        form = self.browser.getForm(name=b'shadowtree-sync-form')
        return form

    def setUp(self):
        super(TestControlPanelFunctional, self).setUp()
        self.app = self.layer[b'app']
        self.portal_url = self.portal.absolute_url()
        self.browser = z2.Browser(self.app)
        self.browser.handleErrors = False

    def test_access_requires_permission(self):
        self._populate()
        transaction.commit()
        url = self._get_uut()

        self._set_credentials(b'unknown-user', b'S3cr3t')
        self.assertRaises(Unauthorized, self.browser.open, url)

        self._set_credentials(pa_testing.TEST_USER_NAME,
                              pa_testing.TEST_USER_PASSWORD)
        self.browser.open(url)

        self._set_credentials(pa_testing.SITE_OWNER_NAME,
                              pa_testing.SITE_OWNER_PASSWORD)
        self.browser.open(url)

    def test_form_shadowtree_synchronised(self):
        self._populate()
        transaction.commit()
        self._set_credentials(pa_testing.SITE_OWNER_NAME,
                              pa_testing.SITE_OWNER_PASSWORD)
        self.browser.open(self._get_uut())
        self.assertRaises(LookupError, self.browser.getControl, name=b'sync')
        self.assertIn(b'shadow tree is synchronised',
                      self.browser.contents.lower())

    def test_form_shadowtree_unsynchronised(self):
        form = self._get_form_after_populate_and_reinstall()
        self.assertTrue(form)
        button = form.getControl(name=b'sync')
        self.assertTrue(button)

    def test_sync(self):
        form = self._get_form_after_populate_and_reinstall()
        form.submit()
        self.assertIn(b'Synchronisation complete', self.browser.contents)
        self.assertIn(b'shadow tree is synchronised',
                      self.browser.contents.lower())
