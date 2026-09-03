==================
Grant permissions
==================

django-finder controls access with access control lists rather than Django's model
permissions. Each file and folder carries a list of
:class:`~finder.models.permission.AccessControlEntry` rows, each granting a privilege to a
principal. See :doc:`../explanation/permissions` for the model behind this.


Give a group read access to a folder
====================================

.. code-block:: python

    from django.contrib.auth.models import Group

    from finder.models.permission import AccessControlEntry, Privilege

    AccessControlEntry.objects.create(
        inode=folder.id,
        group=Group.objects.get(name='Editors'),
        privilege=Privilege.READ,
    )

A principal is a user, a group, or everyone. They are mutually exclusive: set ``user``, or
``group``, or neither — an entry with neither applies to everyone.


Available privileges
====================

.. list-table::
   :header-rows: 1
   :widths: 20 10 70

   * - Privilege
     - Value
     - Grants
   * - ``READ``
     - 1
     - Open a folder and see its contents; see a file and use or copy it.
   * - ``WRITE``
     - 2
     - Upload into a folder, rename it, reorder and move files out of it; replace a file and
       edit its metadata.
   * - ``READ_WRITE``
     - 3
     - Both of the above.
   * - ``ADMIN``
     - 4
     - Change the permissions of the file or folder.
   * - ``FULL``
     - 7
     - All of the above.


Set up a drop box
=================

A folder with ``WRITE`` but no ``READ`` lets users upload but not see what anyone else
uploaded:

.. code-block:: python

    AccessControlEntry.objects.create(
        inode=folder.id,
        privilege=Privilege.WRITE,  # no principal: applies to everyone
    )


Make new files inherit permissions
==================================

:class:`~finder.models.permission.DefaultAccessControlEntry` acts as a template. Entries
attached to a folder are copied onto every file and folder created inside it, or moved into
it.

.. code-block:: python

    from finder.models.permission import DefaultAccessControlEntry

    DefaultAccessControlEntry.objects.create(
        folder=folder,
        group=Group.objects.get(name='Editors'),
        privilege=Privilege.READ_WRITE,
    )

.. todo::

   Document how this is done from the admin interface rather than the shell — this how-to is
   currently ORM-only, which is the wrong altitude for the audience.

.. todo::

   State the rules for who may change permissions and ownership: only superusers and the
   owner may change an object's permissions, and only a superuser may change its owner.
   Confirm against ``finder/models/permission.py`` and the admin before publishing.
