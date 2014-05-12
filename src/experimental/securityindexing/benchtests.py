from __future__ import print_function
from Testing.makerequest import makerequest
from plone import api
from zope.component.hooks import setSite
from zope.component.hooks import setSite

from collections import defaultdict
from string import ascii_lowercase

def _make_folder(id_, parent):
    return api.content.create(type='Folder',
                              container=parent,
                              id=id_)


C = 0

def create_content_tree(parent, nwide, ndeep, level=0, verbose=False):
    global C
    if ndeep == 0:
        return
    ndeep -= 1
    siblings = []
    for i in range(nwide):
        fid = ascii_lowercase[i]
        f = _make_folder(fid, parent=parent)
        siblings.append(f)
        C += 1
    if verbose:
        print('/'.join(f.getPhysicalPath()[:-1]))
        print(' ' * level, ', '.join(s.getId() for s in siblings))
    level += 1
    for sibling in siblings:
        create_content_tree(sibling, nwide, ndeep, level=level)

def runtest(app, nwide, ndeep):
    setup(app)
    portal = api.portal.get()
    create_content_tree(portal, nwide, ndeep)

def setup(app):
    portal = app.objectValues('Plone Site')[0]
    setSite(portal)
    portal.clearCurrentSkin()
    app = makerequest(app)
    setSite(portal)
    # also set up portal_skins stuff
    portal.clearCurrentSkin()
    portal.setupCurrentSkin(app.REQUEST)

if __name__ == '__main__':
    runtest(app, 4, 4)
    portal = api.portal.get()

