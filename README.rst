.. image:: https://api.travis-ci.org/netsight/experimental.securityindexing.png
  :target: https://travis-ci.org/netsight/experimental.securityindexing

.. image:: https://coveralls.io/repos/netsight/experimental.securityindexing/badge.png
  :target: https://coveralls.io/r/netsight/experimental.securityindexing


=============================
experimental.securityindexing
=============================

Design
======

What is the optimisation this package attempts to perform?
----------------------------------------------------------
In a stock Plone (4.x or 5.x) site, when adding roles to users or groups via the @@sharing action
on the current `context` (content item).
The context item has the following API, which when invoked which causes some sites,
depending on structure and complexity, to suffer performances issues:

  Products.CMFCore.intrefaces.ICatalogAware.reindexObjectSecurity(skip_self=False)
      
`reindexObject` security is invoked on the context that local roles are being manipulated upon
in order to reflect the changes in the allowedUsersAndRoles keyword index in the catalog.

This index used by Plone to determine which content a user can see when ZCatalog.searchResults is 
involved (e.g Site Search).

Within a Plone 4.x or 5.x, the two implementations of the `reindexObjectSecurity` API are: 

  RIS-1. Products.CMFCore.CMFCatalogAware.CatalogAware.reindexObjectSecuity(skip_self=False)
         Indexes the content item (self). The keyword parameter skip_self will be False when invoked from
         the @@sharing action.
         For each child node in the content tree "beneath" this content item, fetch that object 
         (ultimately via the ZCatalog.unrestrictedTraverse API) and reindex each one, unconditionally.
     
  RIS-2. Products.Archetypes.CatalogMultiplex.CatalogMultiplex    
         The archetypes tool is used to look up all catalogs that have been registered for the `meta_type`
         of the content item (self).
         For each catalog, the same algorithm as above (1.) is re-implemented (The base class method is not called).
 
 
 The expensive operations are:
   1. "Waking up" each child node via `unrestrictedTraverse`
   2. When any local roles of significance are assigned to the object,
      the indexer for local roles (Products.CMFPlone.CatalogTool.allowedRolesAndUsers) 
      invokes Products.PlonePAS.plugins.local_roles.LocalRolesManager.getAllLocalRolesInContext API,
      which performs the following algorithm for each object to be indexed:
       
      1. Acquire the inner context.
      2. acquire the content object and it's parent.
         and calculate the unique set of local roles for the content object.
      3. If __ac_block_local_roles__ is not set,  exit and returns the local roles calculated.
      3. Repeats 2. until a parent is None (root of the tree).
      

The goals of any solution to address the afore described performance issue(s) are:
 
  1. Wake up as few objects as possible
  2. Where possible, avoid reindexing an object


The following o the scheme envisioned to optimise the above algorithm:

  1. When an object is indexed for the first time `CatalogTool.indexObject`,
     persist a unique token representing the unique set of local roles and the __ac_local_roles_block__
     flag, along with the object's id and physical path in a "shadow tree" which has
     the same form as the main content tree (ZODB).
   
  2. Avoid reindexing where possible, avoid waking up content objects:
   
    2.1 Given an item of content `obj`, determine the set of child objects that need to be re-indexed,
        retrieve the node corresponding to the `obj` from the shadow tree, and each node representing 
        `obj`'s corresponding descendants, and group these nodes by the unique local roles. 
    
    2.2 For each group of nodes, retrieve the content object corresponding to the first node in the group.
    
    2.3 Ask the first object for it's `allowedRolesAndUsers` (aka local roles)
    
    2.4 Index each node in group, supplying a faux object (either the shadow node or some other 
        object standing-in for the content object)


Implementations
===============

The above algorithm was formed whilst attempting an initial implementation,
which at time of writing, resides at `https://github.com/netsight/experimental.localrolesindex`,
where it was chosen to implement a new catalog index type `LocalRolesIndex`.

This proved to be slightly `too low in the stack`.
We decided to move the site of the implementation, the problems encountered were:

  Testing - too many hoops to jump through:

    The algorithm requires retrieval of content objects via the portal catalog,
    or acquisition, both of which require supplying objects which are wrapped by
    appropriate objects which are defined elsewhere in Plone.
    
  Encapsulation - the wrong level:
    
    Due to the requirement to index descendant objects, the algorithm must invoke
    `unrestrictedTraverse`.  
    The `allowedRolesAndUsers` attribute is not provided by the object returned from
    `unrestrictedTraverse`. 
    Plone's `CatalogTool` wraps the object before passing down to the index operations.
    An index implementation does not, and should not need to "know" about planes 
    (it is a Zope2 package, which is intended to work in isolation).
         

Proposed solution
=================

Products.CMFCore.CMFCatalogAware.CatalogAware.reindexObjectSecuity
------------------------------------------------------------------
Modify this method to:

  1. Query an adapter (Plone.app.dexterity behaviour) which provides experimental.securityindexing.IARUIndexer
  2. If an adapter was found, the invoke the `index_object` API
  3. Otherwise invoke the default implementation (as described above in RIS-1)
  

Products.Archetypes.CatalogMultiplex.CatalogMultiplex
------------------------------------------------------

  1. For each catalog provided by the AT tool for the content object's meta type,
    1.1 Query an adapter which provides experimental.securityindexing.IARUIndexer
    1.2 If an adapter was found, the invoke the `index_object` API
    1.3 Otherwise invoke the default implementation (as described above in RIS-1)
     

The following presents the call sites of `reindexObjectSecurity` (Plone 5 buildout):

.. code-block:: bash

  find omelette/ -type f -follow -not -name 'test_*' -name '*.py' -exec grep -HnE '[a-z]+\.reindexObjectSec' {} \;

Results:

  * file, match, (comment, context-needs-wrapping-in-proposed-adapter)

  * omelette/Products/CMFPlone/PloneTool.py:878:        obj.reindexObjectSecurity() (caller = acquireLocalRoles, doesn't appear to be used anymore, 0)

  * omelette/Products/CMFCore/WorkflowTool.py:639:            ob.reindexObjectSecurity() (caller = _notifyCreated, 1)

  * omelette/Products/CMFCore/MembershipTool.py:446:            obj.reindexObjectSecurity() (caller = setLocalRoles,  1)

  * omelette/Products/CMFCore/MembershipTool.py:466:            obj.reindexObjectSecurity() (caller = deleteLocalRoles, 1)

  * omelette/Plone/app/workflow/browser/sharing.py:109:                self.context.reindexObjectSecurity() (caller = handle_form, 1)

  * omelette/Plone/app/workflow/browser/sharing.py:549:            context.reindexObjectSecurity() (caller = update_inherit, 1)

  * omelette/Plone/app/workflow/browser/sharing.py:606:            self.context.reindexObjectSecurity() (caller = update_role_settings, 1)

  * omelette/Plone/app/iterate/subscribers/workflow.py:61:    event.working_copy.reindexObjectSecurity(et) (caller = handleCheckout, 1)


.. code-block:: python

    class IARUIndexer(zope.interface.Interface):
        
        def index_object(obj):
            """Index the security information pertaining to object."""


.. code-block:: python

    @zope.interface.implementer(ICatalogAware, IARUIndexer) # ICatalogAware covers DX and AT
    @zope.component.adapter(IPortalContent, ICatalogTool) # adapt any content object (DX and AT) and catalog tool
    class ARUIndexer(object):

        def __init__(self, context, catalog_tool):
            self.context = context
            self.catalog_tool = catalog_tool
            # lookup a persistent utility we use to store the shadow tree
            # GS migration step will have created the shadow tree and need to have indexed all content
	        # before we can use it
		    # e.g annotation on the portal catalog
       self._shadowtree = IAnnotations(catalog_tool.Indexes['allowedRolesAndUsers'])

        # forward every other attribute to context or raise AttributeError
        def __getattr__(self, name):
	    return getattr(self.context, name)
            
        def reinadexObjectSecurity(self, obj):
            # Implementation a la experiemental.localrolesindex.localrolesindex.LocalRolesIndex.index_object


experimental.securityindexing will be a Plone addon.

TODO
----

Tests:

  Adapt the existing tests in experimental.localrolesindex to be Plone.app.testing based integration tests,
  using 'real' content objects instead of "tests doubles" (i.e the Dummy class).

Implement the algorithm using a pattern as/similar to the adapter described above:
  
  * Decide where to persist the tree.
  * Consider making the shadowtree module its own package
  * Change the shadowtree.Node class to inherit from persistent and delegate to a Btree

Generic Setup profile:
  
  * install profile
    
    * Iterate over all brains in the catalog and create corresponding shadow shadow tree nodes.
    
  * uninstall profile
   
    * Delete the shadow tree (Can this be done optionally)?
    

Misc Notes
==========

The portal root of a Plone site never gets re-indexed, since the reindex* methods provided by 
the single, default implementation:

    Products.CMFPlone.Portal.PloneSite
    
implements the methods of the Products.CMFCore.interfaces.ICatalogAware interface as no-ops.

:author: Matt Russell <mattr@netsight.co.uk>
:date: 2014-05-04
