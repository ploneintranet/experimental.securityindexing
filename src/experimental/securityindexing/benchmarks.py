from __future__ import print_function
import collections
import csv
import datetime
import time
import unittest

import pkg_resources
from plone import api
import plone.app.testing as pa_testing

from . import testing


class BenchTestMixin(object):

    results_path = pkg_resources.resource_filename(__package__, 'bench-results.csv')

    def _write_result(self, duration):      
        pc = api.portal.get_tool('portal_catalog')
        portal = self.layer['portal']
        bench_root_path = '/'.join(portal['bench-root'].getPhysicalPath())
        brains = pc.searchResults(path=bench_root_path)
        n_objects = len(brains)
        items = [
            ('timestamp', datetime.datetime.now().isoformat()),
            ('test-name', self.id()),
            ('duration', duration),
            ('n-objects', n_objects)
        ]
        row = collections.OrderedDict(items)
        with open(self.results_path, 'a') as fp:
            writer = csv.DictWriter(fp, list(row))
            writer.writerow(row)

    def _call_mut(self, obj, *args, **kw):
        method = testing.timed(obj.reindexObjectSecurity)
        return method(*args, **kw)

    def _get_obj(self, path=''):
        return api.content.get('/plone/bench-root' + path)

    def test_reindexObjectSecurity_from_root(self):
        subject = self._get_obj()
        duration = self._call_mut(subject)
        self._write_result(duration)


class VanillaDXBenchTest(BenchTestMixin, unittest.TestCase):

    layer = testing.DX_VANILLA_INTEGRATION
    

class InstalledDXBenchTest(VanillaDXBenchTest):

    layer = testing.DX_INSTALLED_INTEGRATION


class VanillaATBenchTest(BenchTestMixin, unittest.TestCase):

    layer = testing.AT_VANILLA_INTEGRATION
           

class InstalledATBenchTest(VanillaATBenchTest):

    layer = testing.AT_INSTALLED_INTEGRATION



if __name__ == '__main__':
    unittest.main()
