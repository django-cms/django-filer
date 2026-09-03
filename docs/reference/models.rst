======
Models
======

Everything in django-finder is an *inode*: a row identified by a UUID primary key, in one of
several tables, all queryable together. Files and folders are inodes; specialised file types
are models that inherit from — or proxy — the file model.


Core models
===========

``finder.models.inode.InodeModel``
    Abstract base of every file and folder. Carries the UUID primary key, the parent link, the
    name, owner, timestamps and the ``meta_data`` JSON field.

``finder.models.folder.FolderModel``
    A folder. Concrete; holds the tree structure.

``finder.models.file.AbstractFileModel``
    Abstract base of every file model. Adds ``file_name``, ``file_size``, ``sha1``,
    ``mime_type`` and ``tags``, and defines the thumbnail, preview, sample and download URL
    hooks.

``finder.models.file.FileModel``
    The fallback file model, with ``accept_mime_types = ['*/*']``. Anything no other model
    claims ends up here.

``finder.models.ambit.AmbitModel``
    A folder tree's container: root folder, per-user trash folders, and the names of the two
    storage backends. See :doc:`../explanation/ambits`.

``finder.models.filetag.FileTag``
    A tag, scoped to an ambit.

``finder.models.folder.PinnedFolder``
    A user's favourite folder, shown as a tab in the admin.

``finder.models.inode.DiscardedInode``
    Bookkeeping for inodes moved to the trash, so they can be restored to where they came
    from.


Permission models
=================

``finder.models.permission.Privilege``
    ``IntegerChoices``: ``READ`` (1), ``WRITE`` (2), ``READ_WRITE`` (3), ``ADMIN`` (4),
    ``FULL`` (7).

``finder.models.permission.AccessControlEntry``
    One grant of a privilege to a principal on one inode.

``finder.models.permission.DefaultAccessControlEntry``
    A template attached to a folder, copied onto inodes created inside or moved into it.


Model fields
============

``finder.models.fields.FinderFileField``
    A ``UUIDField`` referencing a file. Takes ``ambit`` and ``accept_mime_types``.

``finder.models.fields.FinderFolderField``
    A ``UUIDField`` referencing a folder. Takes ``ambit``.


The file model API
==================

Methods a specialised file model may override. Each takes the ambit, because the storages it
needs live there.

``get_download_url(ambit)``
    URL of the original payload. Defaults to the original storage's URL.

``get_thumbnail_url(ambit)``
    URL of a small square preview for the folder listing. Defaults to
    ``fallback_thumbnail_url``, a static icon.

``get_preview_url(ambit)``
    URL of a larger preview shown in the detail view.

``get_sample_url(ambit)``
    URL of a playable excerpt, for time-based media. Defaults to ``None``.

``store_and_save(ambit, **kwargs)``
    Called after the payload has been received. Extract metadata here, then call ``super()``.

``crop(ambit, path, width, height)``
    Implemented by image models; writes a cropped and scaled copy to the sample storage.

.. todo::

   Replace these hand-written lists with ``autoclass``/``automethod`` directives —
   ``sphinx.ext.autodoc`` is already enabled. That requires ``conf.py`` to configure Django
   (``django.setup()`` against a settings module) before autodoc imports the models.
