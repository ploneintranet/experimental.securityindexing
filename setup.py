##############################################################################
#
# Copyright (c) 2014 Netsight Internet Solutions
# All Rights Reserved.
#
##############################################################################

from setuptools import setup, find_packages


setup(name='experimental.securityindexing',
      version='0.6',
      url='https://github.com/ploneintranet/experimental.securityindexing',
      license='GPLv2',
      description="""\
      Optimises indexing of object security for a Plone site.
      """,
      author='Netsight Internet Solutions',
      author_email='dev@netsight.co.uk',
      long_description=(
          open('README.rst').read() + '\n' +
          open('CHANGES.rst').read()
      ),
      classifiers=[
          'Programming Language :: Python :: 2.7',
          'Framework :: Plone :: 4.0',
          'Framework :: Plone :: 4.1',
          'Framework :: Plone :: 4.2',
          'Framework :: Plone :: 4.3',
      ],
      packages=find_packages('src'),
      namespace_packages=['experimental'],
      package_dir={'': 'src'},
      install_requires=[
          'setuptools',
          'plone.api',
          'zope.annotation',
          'zope.component',
          'zope.interface',
          'Products.Archetypes',
          'Products.CMFCore'
      ],
      extras_require={
          'benchmark': [
              'plone.app.contenttypes[test]',
              'plone.app.testing'
          ],
          'test': [
              'mock',
              'plone.app.contenttypes[test]',
              'plone.app.dexterity[grok]',
              'plone.app.testing',
          ]
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      include_package_data=True,
      zip_safe=False)
