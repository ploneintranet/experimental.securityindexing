from plone import api

from . import shadowtree


def create_shadowtree(configuration_context):
    shadowtree.Node.create_root(context=api.portal.get())
