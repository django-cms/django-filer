============
Architecture
============

Everything is an inode
======================

``InodeModel`` is the abstract base of every file and folder. It gives each row a UUID primary
key rather than an auto-incrementing integer, and that single decision carries most of the
architecture.

Because primary keys are UUIDs, different file types can live in different database tables
while still being addressable — and queryable — as one collection. A folder listing is one
query over a union, not a join across a polymorphic hierarchy. This is what lets django-finder
register specialised models without django-polymorphic, and it is why every model in the
family declares ``app_label = 'finder'``.

A specialised file type is usually a proxy model: no table of its own, just a different
``accept_mime_types`` list and different behaviour. ``ImageFileModel`` is the exception — it
needs columns of its own for width, height and the crop box, so it is concrete, and the PIL
and SVG backends proxy *it*.


Choosing a model for an upload
==============================

On upload the manager matches the file's MIME type against every registered model, most
specific first: an exact match such as ``image/png``, then a subtype wildcard such as
``image/*``, then ``FileModel``'s ``*/*``. Adding a contrib app therefore changes where new
uploads land, and ``manage.py finder reorganize`` moves existing ones to match.


No list views
=============

The admin has no changelist for folders or files — only detail views. Asking for the folder
list redirects you to the detail view of the ambit's root folder, and you navigate from there
the way you would in a file manager. :doc:`user-interface` covers what that navigation looks
like.

.. todo::

   Describe the ``meta_data`` JSON field: what the core writes into it (EXIF, alt text,
   credit, ``sample_start``), how specialised models are expected to use it, and how
   django-entangled surfaces it in forms.

.. todo::

   Explain the trash: ``DiscardedInode``, the per-user trash folder on each ambit, and what
   restoring does.
