===========
Browser API
===========

The admin interface and the file selection widget talk to django-finder over a JSON API. The
endpoints are mounted by including ``finder.browser.urls``:

.. code-block:: python

    urlpatterns = [
        path('finder-api/', include('finder.browser.urls')),
    ]

.. warning::

   This API exists to serve django-finder's own React client. It is not versioned, and its
   shapes change with the client.

.. list-table::
   :header-rows: 1
   :widths: 40 15 45

   * - Endpoint
     - Method
     - Purpose
   * - ``structure/<slug>``
     - GET
     - The folder tree of an ambit, for the sidebar.
   * - ``<uuid:inode_id>/fetch``
     - GET
     - One inode as JSON.
   * - ``<uuid:folder_id>/open`` / ``close``
     - GET
     - Remember a folder's expanded state.
   * - ``<uuid:folder_id>/list``
     - GET
     - The contents of a folder.
   * - ``<uuid:folder_id>/search``
     - GET
     - Search within a folder.
   * - ``<uuid:folder_id>/upload``
     - POST
     - Upload one file into a folder.
   * - ``<uuid:file_id>/change``
     - POST, DELETE
     - Edit a file's metadata, or delete it.
   * - ``<uuid:image_id>/crop``
     - POST
     - Return a cropped and scaled copy of an image.


``crop``
========

The only endpoint that produces an image at a size of your choosing. POST ``width`` and/or
``height``; the missing one is derived from the aspect ratio. The response carries
``cropped_image_url``, the final ``width`` and ``height``, and the image's metadata.

The rendition is cached in the ambit's sample storage under a filename derived from the size
and crop box, so repeated requests for the same size cost nothing.

.. todo::

   The docstring on this view says the ``<finder-file-select>`` widget uses this endpoint, but
   no caller could be found in the ``client/`` sources. Establish whether the endpoint is
   wired up, and document it as public API or mark it internal.
