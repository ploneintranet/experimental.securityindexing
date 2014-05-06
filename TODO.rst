TODO
====

These need to be done before things will work in Plone
------------------------------------------------------

- restarting plone (having previously installed  the index via ZMI) doesn't seem to work
  (id's in shadow tree are None)
- localrolesindex.LocalRoles._index_object_rescursive
  - unrestrictedTraverse needs to be wrapped in IIndexableObject 
- localrolesindex.shadowtree.Node.create_security_token
  - hash needs to sort use frozenset not tuple to make tokens consistent
- Do security declarations need to be added on all methods of persistent classes (Node, Localrolesindex)
  to avoid exposing directly to ZPublisher (invoking via URL) ?





  
