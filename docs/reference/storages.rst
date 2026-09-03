========
Storages
========

``finder.storages.FinderSystemStorage``
=======================================

A ``FileSystemStorage`` subclass that enforces django-finder's path layout: every payload
lives at ``<uuid>/<file name>``, where the UUID is the inode's primary key. Paths that do not
start with a valid UUID are rejected.

Options, passed through ``STORAGES['...']['OPTIONS']``:

``location``
    Filesystem directory holding the files.

``base_url``
    URL prefix under which they are served.

``allow_overwrite``
    Whether saving over an existing name replaces it rather than generating a new one.


Helpers
=======

``finder.storages.delete_directory(storage, dir_path)``
    Remove a directory and its contents from any storage backend, local or remote. Used when
    an inode is erased.

``finder.storages.copy_to_local(storage, file_path)``
    Context manager yielding a local temporary copy of a stored file. Needed by tools that
    cannot read from a Django storage — ``ffmpeg``, for instance.

.. todo::

   State the layout expectations an alternative backend must satisfy to be usable as an
   ambit's original or sample storage, so that projects can plug in their own.
