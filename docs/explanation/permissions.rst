===========
Permissions
===========

django-finder controls access with access control lists, in the sense POSIX and NTFS use the
term: each file and folder carries a list of entries, each granting a privilege to a
principal.

An entry is an ``AccessControlEntry`` row pointing at an inode. Its principal is a user, a
group, or everyone — implemented as a nullable foreign key to ``User`` and one to ``Group``.
They are mutually exclusive: set one, or neither. Neither means everyone.


Why not walk the tree
=====================

Up to django-filer 3, computing a user's permission on a folder meant traversing every
ancestor from that folder to the root. That is a query per level, per folder, on every
listing — and it is why filer became slow on large libraries.

Storing the grants in a separate table turns the same question into a subquery. Filtering a
folder listing for what a user may see is one database query regardless of how deep the tree
is. This is the main reason the permission system was rebuilt rather than ported.


What the privileges mean
========================

``READ`` on a folder lets a user open it and see its contents; on a file, see its thumbnail in
the listing and use or copy the file.

``WRITE`` on a folder lets a user upload into it, rename it, reorder its contents and move
files out of it; on a file, replace it, edit its metadata, and move it — provided both the
source and the target folder are writable.

``ADMIN`` lets a user change the permissions of the file or folder itself.

The combinations ``READ_WRITE`` and ``FULL`` exist for convenience.


The drop box
============

Because read and write are independent, a folder can be writable but not readable. Users can
upload into it and cannot see what anyone else has uploaded. This is deliberate, and it is why
the ``WRITE`` privilege is labelled "Write (Dropbox)".


Inheritance
===========

Permissions on an inode apply to that inode alone. Something else has to say what a *new* file
inside a folder should get, and that is ``DefaultAccessControlEntry``: a separate model,
attached to a folder, acting as a template copied onto everything created inside it or moved
into it.

The two could not be one model. Regular entries must apply only to the object they are
attached to, template entries must apply to descendants, and a single table cannot mean both.


Ownership
=========

Every file and folder has an owner, set to the user who created it. Only a superuser and the
owner may change an object's permissions; only a superuser may change its owner.

Microsoft's write-up of `ACLs in Azure Data Lake storage
<https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-access-control>`_ is a
good explanation of the general model.

.. todo::

   Document how these ACLs interact with Django's own model permissions and the ``is_staff``
   flag — which one is consulted first, and what a user with Django's ``finder`` permissions
   but no ACL entry can do.

.. todo::

   Describe the permission cache: what is cached, when it is invalidated, and what to do if it
   goes stale.
