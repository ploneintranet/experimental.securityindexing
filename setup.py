##############################################################################
#
# Copyright (c) 2014 Netsight Internet Solutions
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from setuptools import setup, find_packages


setup(name='experimental.securityindexing',
      version='0.1dev',
      url='https://github.com/ploneintranet/experimental.securityindexing',
      license='ZPL 2.1',
      description="""\
      Optimises indexing of object security for a Plone site.
      """,
      author='Netsight Internet Solutions',
      author_email='dev@netsight.co.uk',
      long_description=(
          open('README.rst').read() + '\n' +
          open('CHANGES.rst').read()
      ),
      packages=find_packages('src'),
      namespace_packages=['experimental'],
      package_dir={'': 'src'},
      install_requires=[
          'setuptools',
          'five.grok',
          'plone.api'
      ],
      extras_require={
          'test': [
              'mock',
              'plone.app.testing',
              'plone.app.contenttypes[test]',
              'plone.app.event[test]'
          ],
          'dexterity': [
              'plone.app.contenttypes',
              'plone.app.dexterity[grok]',
              'plone.app.event'
          ],
          'benchmarks': [
              # 'click',
              # 'matplotlib',
              # 'numpy'
          ]
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      include_package_data=True,
      zip_safe=False)
