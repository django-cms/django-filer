Settings
========


`FILER_PAGINATE_BY`
-------------------

The number of items (Folders, Files) that should be displayed per page in
admin.

Defaults to `20`

`FILER_SUBJECT_LOCATION_IMAGE_DEBUG`
------------------------------------

Draws a red circle around to point in the image that was used to do the 
subject location aware image cropping.

Defaults to `False`

`FILER_IS_PUBLIC_DEFAULT`
-------------------------

Should newly uploaded files be private or public by default.

Defaults to `False` (new files are private)

`FILER_STATICMEDIA_PREFIX`
--------------------------

The prefix for static media where filer will look for bundled javascript, css
and images.

Defaults to `STATIC_URL/filer/` if `STATIC_URL` is defined and falls back to
`MEDIA_URL/filer/` otherwise. It is the URL where the `filer/static/filer/` 
directory should be served.

`FILER_PUBLICMEDIA_*`
---------------------

`FILER_PUBLICMEDIA_URL`
    the url prefix for public media.
    
    Defaults to `<MEDIA_URL>/filer_public/`
`FILER_PUBLICMEDIA_ROOT`
    the base directory for public media
    
    Defaults to `<MEDIA_ROOT>filer_public/`
`FILER_PUBLICMEDIA_STORAGE`
    the storage backend for public files. can either be a string pointing to
    a storage class or an actual class instance.
    
    Defaults to `filer.storage.PublicFileSystemStorage`
`FILER_PUBLICMEDIA_UPLOAD_TO`
    the function to generate the path relative to the storage root. the 
    default generates a date based path like `2011/05/03/filename.jpg`
    
    Defaults to `filer.utils.generate_filename.by_date`
`FILER_PUBLICMEDIA_THUMBNAIL_URL`
    base url for thumbnails
    
    Defaults to `<MEDIA_URL>filer_public/`
`FILER_PUBLICMEDIA_THUMBNAIL_ROOT`
    base path for thumbnails
    
    Defaults to `<MEDIA_ROOT>filer_public/`
`FILER_PUBLICMEDIA_THUMBNAIL_STORAGE`
    the storage backend to use for thumbnails
    
    Defaults to `filer.storage.PublicFileSystemStorage`

`FILER_PRIVATEMEDIA_*`
---------------------

`FILER_PRIVATEMEDIA_URL`
    the url prefix for private media.
    
    Defaults to `<MEDIA_URL>/filer_private/`
`FILER_PRIVATEMEDIA_ROOT`
    the base directory for private media
    
    Defaults to `<MEDIA_ROOT>filer_private/`
`FILER_PRIVATEMEDIA_STORAGE`
    the storage backend for private files. can either be a string pointing to
    a storage class or an actual class instance.
    
    Defaults to `filer.storage.PrivateFileSystemStorage`
`FILER_PRIVATEMEDIA_UPLOAD_TO`
    the function to generate the path relative to the storage root. the 
    default generates a date based path like `2011/05/03/filename.jpg`
    
    Defaults to `filer.utils.generate_filename.by_date`
`FILER_PRIVATEMEDIA_THUMBNAIL_URL`
    base url for thumbnails
    
    Defaults to `<MEDIA_URL>filer_private/`
`FILER_PRIVATEMEDIA_THUMBNAIL_ROOT`
    base path for thumbnails
    
    Defaults to `<MEDIA_ROOT>filer_private/`
`FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE`
    the storage backend to use for thumbnails
    
    Defaults to `filer.storage.PrivateFileSystemStorage`
`FILER_PRIVATEMEDIA_SERVER`
    the server backend to use to serve the files with. The default serves the
    file entirely with django. This is not what you want on a production server.
    Use one of the other server backends instead.
    
    Defaults to `filer.server.backends.default.DefaultServer`

`FILER_NGINX_PROTECTED_LOCATION`
    the relative location for the nginx file server. see nginx storage backend
    for details.
    
    Defaults to `"protected_media"`

