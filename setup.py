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

_DESCRIPTION = """\
A package for Plone which provlides adapters for optimising
indexing of security information for content objects.
"""

setup(name='experimental.securityindexing',
      version='0.1dev',
      url='https://github.com/wengole/experimental.securityindexing',
      license='ZPL 2.1',
      description=_DESCRIPTION,
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
          'plone.api',
      ],
      extras_require={
          'test': [
              'plone.app.contenttypes',
              'plone.app.event',
              'plone.app.robotframework',
              'plone.app.testing',
              'mock'
          ]
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      include_package_data=True,
      zip_safe=False)
