from zope import interface
from zope.annotation.interfaces import IAnnotations
import plone.app.testing as pa_testing


@interface.implementer(IAnnotations)
class FakePlonePortal(dict):
    """A fake Plone portal object for testing purposes."""

    def getId(self):
        return pa_testing.PLONE_SITE_ID
