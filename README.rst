.. image:: https://api.travis-ci.org/ploneintranet/experimental.securityindexing.png
  :target: https://travis-ci.org/ploneintranet/experimental.securityindexing

.. image:: https://coveralls.io/repos/ploneintranet/experimental.securityindexing/badge.png
  :target: https://coveralls.io/r/ploneintranet/experimental.securityindexing


=============================
experimental.securityindexing
=============================

Installation
============

To install this package, add `experimental.securityindexing` to your Plone sites'
eggs and re-run buildout:

.. code-block: ini

  [buildout]
  ...
  eggs += experimental.securityindexing


Testing it out
--------------
Installation is as above, but add the `benchmarks` extra:

.. code-block: ini

  [buildout]
  ...
  eggs += experimental.securityindexing [benchmarks]

Please read the `benchmark docs`_ for details.


Description
===========
This package aims to address a long-standing performance issue in Plone: 

  When adding roles to users or groups via the @@sharing action
  on the current `context` (content item).
  The context item has the following API, which when invoked which causes some sites,
  depending on structure and complexity.

Existing behaviour
==================
When local roles are assigned to user on a given folderish content item, 
the folder will be indexed and all of it's descendants (child folders) -
unconditionally.

Depending upon the combination of:

  * The structure of the tree

  * The number of descendant content items (depth and breath of the sub-tree
    "beneath" the object being edited)

This behaviour is currently implemented twice (Dexterity and Archetypes),
by the method `reindexObjectSecurity`. This method invoked on the context 
that local roles are being manipulated upon, in order to reflect the changes in the 
`allowedUsersAndRoles` `Keywordindex` in the `ZCatalog`.

This index used by Plone to determine which content a user can see when ZCatalog.searchResults is 
involved (e.g Site Search).

Within a Plone 4.x or 5.x, the two implementations of the `reindexObjectSecurity` API are: 

  - Products.CMFCore.CMFCatalogAware.CatalogAware.reindexObjectSecuity(skip_self=False):
    Indexes the content item (self). The keyword parameter skip_self 
    will be False when invoked from the @@sharing action.
    For each child node in the content tree "beneath" this content item, 
    fetch that object, ultimately via the ZCatalog.unrestrictedTraverse API, 
    and re-index each one, unconditionally.
     
  - Products.Archetypes.CatalogMultiplex.CatalogMultiplex    
    The archetypes tool is used to look up all catalogs that have 
    been registered for the `meta_type` of the content item (self).

N.B Both these implementations implement the Products.CMFCore.interfaces.ICatalogAware
    interface.

The expensive operations seem to be:

   1. "Waking up" each child node via `unrestrictedTraverse`

   2. When any local roles of significance are assigned to the object,
      the indexer for local roles (Products.CMFPlone.CatalogTool.allowedRolesAndUsers) 
      invokes Products.PlonePAS.plugins.local_roles.LocalRolesManager.getAllLocalRolesInContext API,
      which performs the following algorithm for each object to be indexed:
       
      1. Acquire the inner context.

      2. acquire the content object and it's parent.
         and calculate the unique set of local roles for the content object.

      3. If __ac_block_local_roles__ is not set,  exit and returns the local roles calculated.

      4. Repeats 2. until a parent is None (root of the tree).
      

The goals of any solution to address the afore described performance issue(s) are:
 
  1. Wake up as few objects as possible.

  2. Where local roles information has not changed, avoid re-indexing.

The following scheme was envisioned to optimise the above algorithm:

  1. When an object is indexed for the first time `CatalogTool.indexObject`,
     persist a unique token representing the unique set of local roles and the __ac_local_roles_block__
     flag, along with the object's id and physical path in a "shadow tree" which has
     the same form as the main content tree (ZODB).
   
  2. Avoid re-indexing where possible, avoid waking up content objects:
   
    2.1 Given an item of content `obj`, determine the set of child objects that need to be re-indexed,
        retrieve the node corresponding to the `obj` from the shadow tree, and each node representing 
        `obj`'s corresponding descendants, and group these nodes by the unique local roles. 
    
    2.2 For each group of nodes, retrieve the content object corresponding to the first node in the group.
    
    2.3 Ask the first object for it's `allowedRolesAndUsers` (aka local roles)
    
    2.4 Index each node in group, supplying a faux object (either the shadow node or some other 
        object standing-in for the content object)

Credit
======
This work has been done as part of the `Plone Intranet project`_. 
Work sponsored by `Netsight Internet Solutions`_.


.. _`Netsight Internet Solutions`: http://www.netsight.co.uk
.. _`Plone Intranet project`: http://github.com/ploneintranet
.. _`benchmark docs`: docs/benchmarks.rst

