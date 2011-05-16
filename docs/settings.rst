.. _settings:

Settings
========


``FILER_IS_PUBLIC_DEFAULT``
---------------------------

Should newly uploaded files have permission checking disabled (be public) by default.

Defaults to `False` (new files have permission checking enabled, are private)

.. _FILER_STATICMEDIA_PREFIX:

``FILER_STATICMEDIA_PREFIX``
----------------------------

The prefix for static media where filer will look for bundled javascript, css
and images.

Defaults to ``<STATIC_URL>/filer/`` if ``STATIC_URL`` is defined. Otherwise
falls back to ``<MEDIA_URL>/filer/``. It is the URL where the ``static/filer/`` 
directory should be served.

``FILER_PUBLICMEDIA_*``
-----------------------

``FILER_PUBLICMEDIA_ROOT``
    The base directory for public (without permission checks) media.
    
    Defaults to ``<MEDIA_ROOT>/filer/``
    
``FILER_PUBLICMEDIA_URL``
    The url prefix for public (without permission checks) media.
    
    Defaults to ``<MEDIA_URL>/filer/``
    
``FILER_PUBLICMEDIA_STORAGE``
    The storage backend for public (without permission checks) files. Must be
    an instance of a storage class.
    
    Defaults to ``filer.storage.PublicFileSystemStorage`` using 
    ``FILER_PUBLICMEDIA_ROOT`` and ``FILER_PUBLICMEDIA_URL`` as ``location`` and
    ``base_url``.
    
``FILER_PUBLICMEDIA_UPLOAD_TO``
    The function to generate the path relative to the storage root. The 
    default generates a date based path like ``2011/05/03/filename.jpg``. This
    will be applied with the current date whenever a file is uploaded or moved
    between public (without permission checks) and private (with permission
    checks) storages.
    
    Defaults to ``'filer.utils.generate_filename.by_date'``
    
``FILER_PUBLICMEDIA_THUMBNAIL_ROOT``
    Same as ``FILER_PUBLICMEDIA_ROOT`` but for thumbnails.
    
    Defaults to ``<MEDIA_ROOT>/filer_thumbnails/``
    
``FILER_PUBLICMEDIA_THUMBNAIL_URL``
    Same as ``FILER_PUBLICMEDIA_URL`` but for thumbnails.
    
    Defaults to ``<MEDIA_URL>/filer_thumbnails/``
    
``FILER_PUBLICMEDIA_THUMBNAIL_STORAGE``
    Same as ``FILER_PUBLICMEDIA_STORAGE`` but for thumbnails
    
    Defaults to ``filer.storage.PublicFileSystemStorage`` using 
    ``FILER_PUBLICMEDIA_THUMBNAIL_ROOT`` and ``FILER_PUBLICMEDIA_THUMBNAIL_URL`` as
    ``location`` and ``base_url``.
    
``FILER_PRIVATEMEDIA_*``
------------------------

``FILER_PRIVATEMEDIA_ROOT``
    The base directory for private (with permission checks) media.
    
    Defaults to ``<MEDIA_ROOT>/../smedia/filer/``
    
``FILER_PRIVATEMEDIA_URL``
    The url prefix for private (with permission checks) media.
    
    Defaults to ``/smedia/filer/``
    
``FILER_PRIVATEMEDIA_STORAGE``
    The storage backend for private (with permission checks) files. Must be
    an instance of a storage class.
    
    Defaults to ``filer.storage.PublicFileSystemStorage`` using 
    ``FILER_PRIVATEMEDIA_ROOT`` and ``FILER_PRIVATEMEDIA_URL`` as ``location`` and
    ``base_url``.
    
``FILER_PRIVATEMEDIA_UPLOAD_TO``
    The function to generate the path relative to the storage root. The 
    default generates a date based path like ``2011/05/03/filename.jpg``. This
    will be applied with the current date whenever a file is uploaded or moved
    between public (without permission checks) and private (with permission
    checks) storages.
    
    Defaults to ``'filer.utils.generate_filename.by_date'``
    
``FILER_PRIVATEMEDIA_THUMBNAIL_ROOT``
    Base path for thumbnails
    
    Defaults to ``<MEDIA_ROOT>/../smedia/filer_thumbnails/``
    
``FILER_PRIVATEMEDIA_THUMBNAIL_URL``
    Base url for thumbnails.
    
    Defaults to ``/smedia/filer_thumbnails/``
    
``FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE``
    Same as ``FILER_PRIVATEMEDIA_STORAGE`` but for thumbnails.
    
    Defaults to ``filer.storage.PrivateFileSystemStorage`` using 
    ``FILER_PRIVATEMEDIA_THUMBNAIL_ROOT`` and ``FILER_PRIVATEMEDIA_THUMBNAIL_URL``
    as ``location`` and ``base_url``.
    
``FILER_PRIVATEMEDIA_SERVER``
    The server backend to use to serve the private (with permission checks)
    files with. The default serves the file entirely with django. This is not
    what you want on a production server. Use one of the other server backends
    in production instead:
        
    * ``filer.server.backends.nginx.NginxXAccelRedirectServer``
    * ``filer.server.backends.xsendfile.ApacheXSendfileServer``
    
    Defaults to ``filer.server.backends.default.DefaultServer``
    

``FILER_PAGINATE_BY``
---------------------

The number of items (Folders, Files) that should be displayed per page in
admin.

Defaults to `20`

``FILER_SUBJECT_LOCATION_IMAGE_DEBUG``
--------------------------------------

Draws a red circle around to point in the image that was used to do the 
subject location aware image cropping.

Defaults to `False`
