==============
Manage ambits
==============

An ambit is a self-contained folder tree: one root folder, one trash folder per user, its own
tag vocabulary, and its own pair of storage backends. Ambits are managed from the command
line, not the admin. See :doc:`../explanation/ambits` for what they are for.


The ambit you already have
==========================

You do not have to create the first one. When a project has no ambit at all, the
``finder.0002_default_ambit`` migration creates one named by ``FINDER_DEFAULT_AMBIT``
(``public`` by default) on the storages described in :doc:`configure-storages`, with a root
folder that grants read and write to every signed-in user.

To manage the ambits entirely yourself, opt out **before migrating for the first time**:

.. code-block:: python

    FINDER_CREATE_DEFAULT_AMBIT = False

The setting is only read while that migration is applied. Flipping it afterwards changes
nothing — use ``add-ambit`` and ``delete-ambit`` from then on.


List the ambits
===============

.. code-block:: shell

    ./manage.py finder list-ambits

Prints the slug, name, site, admin site and both storages of every ambit. A storage is shown
as its ``STORAGES`` alias followed by the backend class, so a misconfigured ambit is visible
at a glance:

.. code-block:: text

    Slug: public, Name: Public, Site: None, Admin: None,
    Storage: finder_public (FinderSystemStorage),
    Sample Storage: finder_public_samples (FinderSystemStorage)

    Slug: press, Name: Press, Site: None, Admin: None,
    Storage: finder_press (not configured!),
    Sample Storage: finder_public_samples (FinderSystemStorage)


Create another ambit
====================

.. code-block:: shell

    ./manage.py finder add-ambit <slug> \
        --values name="Media Library" \
                 storage=finder_public \
                 sample_storage=finder_public_samples

``--values`` accepts ``key=value`` pairs:

``name``
    Display name shown in the admin sidebar. Defaults to the capitalised slug.

``storage``
    Name of the ``STORAGES`` entry holding uploaded originals. Defaults to
    ``finder_public``, which django-finder derives from your ``default`` storage unless you
    declare it — see :doc:`configure-storages`.

``sample_storage``
    Name of the ``STORAGES`` entry holding thumbnails and samples. Defaults to
    ``finder_public_samples``, derived the same way.

``site``
    Numeric ID of a ``django.contrib.sites`` site, to restrict the ambit to it.

``admin``
    Name of an admin site, to restrict the ambit to it.


Change an ambit
===============

.. code-block:: shell

    ./manage.py finder edit-ambit <slug> --values name="Press Photos"

Takes the same ``--values`` keys as ``add-ambit``, plus ``slug`` to rename the ambit itself:

.. code-block:: shell

    ./manage.py finder edit-ambit default --values slug=public

Renaming leaves the folder tree untouched, but the slug is part of every folder URL in the
admin, and a :class:`~finder.models.fields.FinderFileField` naming the old one stops
resolving. Changing ``storage`` or ``sample_storage`` moves no files — see
:doc:`configure-storages`.


Delete an ambit
===============

.. code-block:: shell

    ./manage.py finder delete-ambit <slug>

Add ``--erase-files`` to also remove the payloads from storage. Without it the database rows
go and the files stay.

.. warning::

   ``--erase-files`` is irreversible. There is no confirmation prompt.

.. todo::

   Verify the exact behaviour of ``delete-ambit`` without ``--erase-files`` — in particular
   whether sample storage is cleaned up, and what happens to files referenced by a
   ``FinderFileField`` on another model.


Maintenance subcommands
=======================

``reorganize <slug>``
    Walks every file in the ambit and reassigns it to the model matching its MIME type. Run
    this after adding a contrib app to an existing installation, so that files already
    uploaded are picked up by their new specialised model.

``reorder <slug>``
    Recomputes the ``ordering`` value of every file in every folder.
