from zope import interface
from zope.annotation.interfaces import IAnnotations


_PORTAL_ID = 'plone'


@interface.implementer(IAnnotations)
class FakePlonePortal(dict):
    """A fake Plone portal object for testing purposes."""

    def getId(self):
        return _PORTAL_ID
