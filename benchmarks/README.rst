============
 Benchmarks
============

The buildout for this project contains some basic 
benmarks which aim to measure the difference in speed
between performing actions which change the `allowedRolesAndUsers` 
index in ZCatalog.

There are currently four o perations which can be run:
 
  1. Setting a local role for a user on a folder at the root of the site.
  
  2. Setting a local role block on a folder at the root of the site.

  3. Transistioning a folder a the root of the site from private to published.

  4. Simulating the user pressing save on the sharing tab without changing any settings.


 Buildout
==========

The easiest way to run the benchmarks it to checkout this project and run buildout:

.. code-block: bash

   [buildout]
   eggs += experimental.securityindexing[test,benchmarks]
   ...

.. code-block: bash
  
   $ bin/buildout -c dev.cdg


Running
=======

These benchmarks can (and should!) be run for both Dexterity (DX) and Archetypes (AT)
content types. 

In order to control how many folders the benchmarks create, please set the following 
environment variables accordingly:

.. code-block: bash

BENCHMARK_N_LEVELS=2
BENCHMARK_N_SIBLINGS=2



The folowing will run all benchmarks for four times:

   1. DX (without package installed)

   2. DX (with package installed)

   3. AT (without package installed)

   4. AT (with package installed)

.. code-block: bash

   $ bin/benchmark-dx
   $ bin/benchmark-at

    
