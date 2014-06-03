============
 Development
============

All development is done with github_.

Please raise issues found on the issue tracker and submit 
pull-requests for patches.


Contributing guidelines
=======================

1. Configure buildout

.. code-block: ini

   [buildout]
   eggs += experimental.securityindexing[test,benchmarks]

2. Running tests

.. code-block: bash

   $ bin/buildout -c dev.cfg
   $ bin/test

3. Check coverage and flake8 before committing.
   The master branch is tested on travis, but doing will help us out!

.. code-block: bash
   
   $ bin/createcoverage
   $ bin/flake8 src/experimental

4. If all the above tests have passed, and you'd like to contribute a 
   pull-request, please add yourself to the `contributors`_ file.

5. Issue the pull-request on github_. 

Thanks!


.. _github: http://github.com/ploneintranet/experimental.securityindexing
.. _contributors: CONTRIBUTORS.rst
