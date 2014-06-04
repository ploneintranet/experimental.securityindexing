TODO
====

  * Handle skip_self in ObjectSecurity.reindex/reindexObjectSecurity

  * Try and find a better way to handle when the reindexObjectSecurity method(s) get patched.
    Currently, we have a global ZCA utility 'managing' a SimpleItem tool which is site local.
    Previously attempted to conditionally initialise and persist the shadow tree tool in a GS import step,
    but this fails because reindexObjectSecurity is apparently called *before* import steps are executed.


