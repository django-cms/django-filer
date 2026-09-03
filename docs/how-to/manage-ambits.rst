==============
Manage ambits
==============

An ambit is a self-contained folder tree: one root folder, one trash folder per user, its own
tag vocabulary, and its own pair of storage backends. Ambits are managed from the command
line, not the admin. See :doc:`../explanation/ambits` for what they are for.


List the ambits
===============

.. code-block:: shell

    ./manage.py finder list-ambits

Prints the slug, name, site, admin site and both storage names for every ambit.


Create an ambit
===============

.. code-block:: shell

    ./manage.py finder add-ambit <slug> \
        --values name="Media Library" \
                 storage=finder_public \
                 sample_storage=finder_public_samples

``--values`` accepts ``key=value`` pairs:

``name``
    Display name shown in the admin sidebar. Defaults to the capitalised slug.

``storage``
    Name of the ``STORAGES`` entry holding uploaded originals.

``sample_storage``
    Name of the ``STORAGES`` entry holding thumbnails and samples.

``site``
    Numeric ID of a ``django.contrib.sites`` site, to restrict the ambit to it.

``admin``
    Name of an admin site, to restrict the ambit to it.


Change an ambit
===============

.. code-block:: shell

    ./manage.py finder edit-ambit <slug> --values name="Press Photos"

Takes the same ``--values`` keys as ``add-ambit``.


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
