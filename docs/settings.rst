.. _settings:

Settings
========

``FILER_ENABLE_PERMISSIONS``
----------------------------

Activate the or not the Permission check on the files and folders before 
displaying them in the admin. When set to false it give all the authorization
to staff members.

Defaults to ``True``

``FILER_IS_PUBLIC_DEFAULT``
---------------------------

Should newly uploaded files have permission checking disabled (be public) by default.

Defaults to ``False`` (new files have permission checking enabled, are private)

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

``FILER_PUBLICMEDIA_STORAGE``
    The storage backend for public (without permission checks) files. Must be
    an instance of a storage class.

``FILER_PUBLICMEDIA_UPLOAD_TO``
    The function to generate the path relative to the storage root. The 
    default generates a date based path like ``2011/05/03/filename.jpg``. This
    will be applied with the current date whenever a file is uploaded or moved
    between public (without permission checks) and private (with permission
    checks) storages.

    Defaults to ``'filer.utils.generate_filename.by_date'``

``FILER_PUBLICMEDIA_THUMBNAIL_STORAGE``
    Same as ``FILER_PUBLICMEDIA_STORAGE`` but for thumbnails

``FILER_PUBLICMEDIA_FORMATS_STORAGE``
    Same as ``FILER_PUBLICMEDIA_STORAGE`` but for automatically generated video files
    
``FILER_PRIVATEMEDIA_*``
------------------------

``FILER_PRIVATEMEDIA_STORAGE``
    The storage backend for private (with permission checks) files. Must be
    an instance of a storage class.
    
    default generates a date based path like ``2011/05/03/filename.jpg``. This
    will be applied with the current date whenever a file is uploaded or moved
    between public (without permission checks) and private (with permission
    checks) storages.
    
    Defaults to ``'filer.utils.generate_filename.by_date'``
    
``FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE``
    Same as ``FILER_PRIVATEMEDIA_STORAGE`` but for thumbnails.
    
    Defaults to ``filer.storage.PrivateFileSystemStorage`` using 
    ``FILER_PRIVATEMEDIA_THUMBNAIL_ROOT`` and ``FILER_PRIVATEMEDIA_THUMBNAIL_URL``
    as ``location`` and ``base_url``.
    
``FILER_PRIVATEMEDIA_FORMATS_STORAGE``
    Same as ``FILER_PRIVATEMEDIA_STORAGE`` but for automatically generated video files.

``FILER_PRIVATEMEDIA_SERVER``
    The server backend to use to serve the private (with permission checks)
    files with. The default serves the file entirely with django. This is not
    what you want on a production server. Use one of the other server backends
    in production instead:
        
    * ``filer.server.backends.nginx.NginxXAccelRedirectServer``
    * ``filer.server.backends.xsendfile.ApacheXSendfileServer``
    
    Defaults to ``filer.server.backends.default.DefaultServer``

``FILER_PRIVATEMEDIA_FORMATS_SERVER``
    Same as ``FILER_PRIVATEMEDIA_SERVER`` but for automatically generated video files

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

``FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS``
-------------------------------------------------

Regular users are not allowed to create new folders at the root level, only
subfolders of already existing folders, unless this setting is set to ``True``.

Defaults to `False`

``FILER_SOURCE_VIDEO_FORMATS``
------------------------------

Formats recognized as video file formats. Used by djando-filer to identify video files when
uploading a new file. The value should be a list of file extensions without the leading dot.

Defaults to `('mp4', 'avi', 'wmv', 'mov', 'mpg')`

``FILER_VIDEO_FORMATS``
-----------------------

Formats that uploaded video files will be automatically converted to (if the cronjob is set and
ffmpeg available).

Defaults to `('flv', 'mp4', 'webm')`

``FFMPEG_CHECK_CMD``
--------------------

Command line executed to check video dimensions.

Defaults to `"ffmpeg -i %(input_file)s"`

``FFMPEG_CMD``
--------------

Command line executed to convert a video to a given format.

Defaults to `"ffmpeg -i %(input_file)s -y -b 2326k -ar 44100 -ab 224k -ac 2 -f %(format)s %(dimensions)s %(target_file)s"`

``GRABIMG_CMD``
---------------

Command line executed to grab a poster image for a video. The default is to grab a frame at 2s and
create a pgn file.

Defaults to `"ffmpeg -y -i %(input_file)s -vframes 1 -ss 00:00:02 -an -vcodec png -f rawvideo %(dimensions)s %(target_file)s"`

``FFMPEG_TARGET_DIMENSIONS``
----------------------------

To resize the converted videos to fixed dimensions. The value should be in the <width>x<height> format.
Leave blank to keep the original video dimensions.

Defaults to `""`

