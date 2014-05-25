from __future__ import print_function
import io
import logging

# Cannot use package relative imports here
# since this uninstall script is loaded by ancient dragons
# into an Extensoin method down in z2 (i.e not imported directly in python)
import experimental.securityindexing.utilities as esu


def uninstall(portal, reinstall=False):
    pkg_name = esu.__package__
    logger = logging.getLogger(pkg_name)
    out = io.BytesIO()
    try:
        esu.ShadowTreeTool.delete_from_storage(portal)
    except Exception as e:  # pragma: no cover
        print(b'failed (traceback follows):', file=out)
        print(e, file=out)
        logger.exception(e)
    else:
        msg = b'Removed shadowtree...'
        logger.info(msg)
        print(msg, file=out)
    if reinstall:  # pragma: no cover
        portal_setup = portal.portal_setup
        default_profile_id = b'profile-%s:default' % (pkg_name,)
        portal_setup.runAllImportStepsFromProfile(default_profile_id)
    return out.getvalue()
