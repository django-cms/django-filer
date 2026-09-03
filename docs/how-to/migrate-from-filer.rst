=========================
Migrate from django-filer
=========================

django-finder ships a management command that walks an existing django-filer installation and
recreates its folders and files in a finder ambit.

.. warning::

   Take a backup of your database and media files first. The command has not been through a
   release cycle yet.


Before you start
================

Both ``filer`` and ``finder`` must be installed and in ``INSTALLED_APPS`` at the same time,
with filer's tables intact and its media files reachable through filer's storages.


Run the migration
=================

.. code-block:: shell

    ./manage.py filer_to_finder <ambit-slug>

Every filer folder becomes a :class:`~finder.models.folder.FolderModel` under the ambit's
root folder, and every filer file is copied into the ambit's original storage.

.. todo::

   Document precisely what the command does and does not carry over. From a first read of
   ``finder/management/commands/filer_to_finder.py`` it migrates folders and images with the
   MIME types ``image/gif``, ``image/jpeg``, ``image/png``, ``image/webp`` and
   ``image/svg+xml``. Confirm — and state — what happens to non-image files, to filer
   permissions, to focal points, to ``FilerFileField`` references on third-party models, and
   whether the command is idempotent.


What has no equivalent
======================

.. todo::

   Write the mapping table from filer concepts to finder ones: ``FILER_*`` settings to
   ``FINDER_*`` settings, ``FolderPermission`` to
   :class:`~finder.models.permission.AccessControlEntry`, easy-thumbnails aliases to
   :doc:`../explanation/thumbnails-and-samples`, ``FilerFileField`` to
   :class:`~finder.models.fields.FinderFileField`, the clipboard, and the ``filer_check``
   command. Say explicitly which have no counterpart.
