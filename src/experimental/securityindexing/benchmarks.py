from __future__ import print_function
import collections
import csv
import datetime
import time
import unittest

import pkg_resources
from plone import api
from plone.app.contenttypes.testing import (
    PLONE_APP_CONTENTTYPES_FIXTURE,
)
from plone.app.event.testing import PAEvent_FIXTURE
import plone.app.testing as pa_testing

from . import testing


class BenchmarkLayer(pa_testing.PloneSandboxLayer):
    """Base class for benchmark layers.

    Ensures that a tree of content is created after installation
    of packages is performed.
    """
    n_wide = 10
    n_deep = 5

    def _sanity_checks(self):
        raise NotImplementedError()
       
    def setUpPloneSite(self, portal):
        pa_testing.setRoles(portal, pa_testing.TEST_USER_ID, ['Manager'])
        pa_testing.login(portal, pa_testing.TEST_USER_NAME)
        super(BenchmarkLayer, self).setUpPloneSite(portal)
        self.top = api.content.create(api.portal.get(), id='bench-root', type='Folder')
        with testing.catalog_disabled():
            testing.create_content_tree(self.top, self.n_wide, self.n_deep)
        catalog = api.portal.get_tool('portal_catalog')
        catalog.clearFindAndRebuild()
        self._sanity_checks()

      
class VanillaDXBenchLayer(BenchmarkLayer):
    """A layer which ensure Dexteity is used for the default content types."""

    defaultBases = (PLONE_APP_CONTENTTYPES_FIXTURE, 
                    PAEvent_FIXTURE, 
                    pa_testing.PLONE_FIXTURE)

    def _sanity_checks(self):
        assert self.top.meta_type.startswith('Dexterity')


class InstalledDXBenchLayer(testing.SecurityIndexingLayerMixin,
                            VanillaDXBenchLayer):
    """A benchmark layer that installs plone.app.contenttypes,
    and this addon package.
    """


class VanillaATBenchLayer(BenchmarkLayer):
    """A Plone 4.3.x layer for benchmarking.

    This layer installs no additional addons.
    """

    def _sanity_checks(self):
        assert self.top.meta_type.startswith('ATFolder')


class InstalledATBenchLayer(testing.SecurityIndexingLayerMixin,
                            VanillaATBenchLayer):
    """A benchmark layer this addon package installed."""


DX_VANILLA_FIXTURE = VanillaDXBenchLayer()
DX_VANILLA_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_VANILLA_FIXTURE,),
    name='VanillaDXLayer:Integration'
)

DX_INSTALLED_FIXTURE = InstalledDXBenchLayer()
DX_INSTALLED_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(DX_INSTALLED_FIXTURE,),
    name='InstalledDXLayer:Integration'
)

AT_VANILLA_FIXTURE = VanillaATBenchLayer()
AT_VANILLA_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_VANILLA_FIXTURE,),
    name='VanillaATLayer:Integration'
)

AT_INSTALLED_FIXTURE = InstalledATBenchLayer()
AT_INSTALLED_INTEGRATION = pa_testing.IntegrationTesting(
    bases=(AT_INSTALLED_FIXTURE,),
    name='InstalledATLayer:Integration'
)



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

    layer = DX_VANILLA_INTEGRATION
    

class InstalledDXBenchTest(VanillaDXBenchTest):

    layer = DX_INSTALLED_INTEGRATION


class VanillaATBenchTest(BenchTestMixin, unittest.TestCase):

    layer = AT_VANILLA_INTEGRATION
           

class InstalledATBenchTest(VanillaATBenchTest):

    layer = AT_INSTALLED_INTEGRATION



if __name__ == '__main__':
    unittest.main()
