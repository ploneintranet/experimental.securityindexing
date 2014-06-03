from plone.app.contenttypes.testing import (
    PLONE_APP_CONTENTTYPES_FIXTURE,
)
import plone.app.contenttypes.tests.robot.variables as pact_robotvars
import plone.app.testing as pa_testing

from .. import testing


INTEGRATION = pa_testing.IntegrationTesting(
    bases=(PLONE_APP_CONTENTTYPES_FIXTURE, testing.FIXTURE),
    name=b'SecurityIndexingLayerDDCT:Integration'
)


class Mixin(object):

    def _check_paths_equal(self, paths, expected_paths):
        # Ignore robot-test-folder created by the
        # p.a.{event,contenttypes} fixture(s)
        robot_test_folder = pact_robotvars.TEST_FOLDER_ID
        exclude = {
            b'/{id}'.format(id=robot_test_folder),
            (b'', pa_testing.PLONE_SITE_ID, robot_test_folder)
        }
        check = super(Mixin, self)._check_paths_equal
        check(paths - exclude, expected_paths - exclude)
