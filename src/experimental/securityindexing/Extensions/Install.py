import io
import logging

# Cannot use package relative imports here
# since this uninstall script is loaded by ancient dragons
# into an Extensoin method down in z2 (i.e not imported directly in python)
import experimental.securityindexing.utilities as esu


def uninstall(portal, reinstall=False):
    if reinstall:  # pragma: no cover
        return
    pkg_name = esu.__package__
    logger = logging.getLogger(pkg_name)
    out = io.BytesIO()
    msg = b'%s: Removing shadowtree... ' % (pkg_name,)
    logger.info(msg)
    out.write(msg)
    try:
        esu.ShadowTreeTool.delete_from_storage(portal)
    except Exception as e:  # pragma: no cover
        out.write(b'failed (traceback follows):')
        out.write(e)
        logger.exception(e)
    else:
        out.write(b'done.')
    return out.getvalue()
