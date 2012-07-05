.. _permissions:

Permissions
===========

.. NOTE:: For the impatient:
          
          * set ``FILER_ENABLE_PERMISSIONS`` to ``True``
          * include ``filer.server.urls`` in the root ``urls.py`` without a 
            prefix

By default files can be uploaded and managed by all staff members based on the
standard django model permissions.
Since the files get uploaded to ``MEDIA_ROOT`` they can be can be downloaded by
everyone.

Optionally permission checking can be activated with the
``FILER_ENABLE_PERMISSIONS`` setting. This allows setting access rights for
editing files in the backend (with the `edit` permission) and downloading the
files (with the `read` permission).
For images the permissions also extend to all generated thumbnails.

To be able to check permissions on the file downloads, a special view is used.
The files are saved in a separate location outside of ``MEDIA_ROOT`` to prevent
accidental serving. By default this is a directory called ``smedia`` that is
located in the parent directory of ``MEDIA_ROOT``.
The smedia directory must **NOT** be served by the webserver directly, because
that would bypass the permission checks.

To hook up the view ``filer.server.urls`` needs to be included in the root
``urls.py``::

    urlpatterns += patterns('',
        url(r'^', include('filer.server.urls')),
    )

.. WARNING:: With the default settings the private files will be served by
             django directly.
             This is not what you'll want in production because performance is
             not very good (especialy with large files).
             See the :ref:`server` topic on how to improve this.