from __future__ import print_function
from collections import defaultdict
import csv
import datetime
import functools
import time
import unittest

from Testing.makerequest import makerequest
from plone import api
from zope.component.hooks import setSite
from zope.component.hooks import setSite
import pkg_resources


from .testing import (
    DX_VANILLA_INTEGRATION, 
    DX_INSTALLED_INTEGRATION
)


def timed(func):
    @functools.wraps(func)
    def timer(*args, **kw):
        start = time.time()
        elapsed = 0
        try:
            func(*args, **kw)
        finally:
            elapsed = time.time() - start
        return elapsed
    return timer


# For debugging (aka netsight.utils.debugging.setup_session)
def setup(app):
    portal = app.objectValues('Plone Site')[0]
    setSite(portal)
    portal.clearCurrentSkin()
    app = makerequest(app)
    setSite(portal)
    # also set up portal_skins stuff
    portal.clearCurrentSkin()
    portal.setupCurrentSkin(app.REQUEST)


class BenchTestMixin(object):

    results_path = pkg_resources.resource_filename(__package__, 'bench-results.csv')

    def _write_result(self, duration):      
        pc = api.portal.get_tool('portal_catalog')
        portal = self.layer['portal']
        bench_root_path = '/'.join(portal['bench-root'].getPhysicalPath())
        brains = pc.searchResults(path=bench_root_path)
        n_objects = len(brains)
        headers = ['timestamp', 'test-name', 'duration', 'n-objects']
        result = dict.fromkeys(headers)
        result['timestamp'] = datetime.datetime.now().isoformat()
        result['test-name'] = self.id()
        result['duration'] = duration
        result['n-objects'] = n_objects
        with open(self.results_path, 'a') as fp:
            writer = csv.DictWriter(fp, headers)
            writer.writerow(result)

    def _call_mut(self, obj, *args, **kw):
        method = timed(obj.reindexObjectSecurity)
        return method(*args, **kw)

    def _get_obj(self, path):
        return api.content.get('/plone/bench-root' + path)

    def test_reindexObjectSecurity(self):
        subject = api.content.get(path='/Plone/a/b')
        duration = self._call_mut(subject)
        self._write_result(duration)


class VanillaDXBenchTest(BenchTestMixin, unittest.TestCase):

    layer = DX_VANILLA_INTEGRATION
    
    def setUp(self):
        super(VanillaDXBenchTest, self).setUp()

    def test_reindexObjectSecurity(self):
        subject = self._get_obj('/a/b')
        duration = self._call_mut(subject)
        self._write_result(duration)
        

class InstalledDexterityBenchTest(VanillaDXBenchTest):

    layer = DX_INSTALLED_INTEGRATION


if __name__ == '__main__':
    unittest.main()
