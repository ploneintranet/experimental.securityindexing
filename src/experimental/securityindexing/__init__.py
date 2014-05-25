from zope.i18nmessageid import MessageFactory


_ = MessageFactory(__package__)


def initialize(context):
    """Old Zope2-style product intitializer.

    This is here to support Extensions.Install.uninstall.
    """
