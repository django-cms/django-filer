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


``FILER_STORAGES``
------------------

A dictionary to configure storage backends used for file storage.

e.g::

    FILER_STORAGES = {
        'public': {
            'main': {
                'ENGINE': 'filer.storage.PublicFileSystemStorage',
                'OPTIONS': {
                    'location': '/path/to/media/filer',
                    'base_url': '/smedia/filer/',
                },
                'UPLOAD_TO': 'filer.utils.generate_filename.by_date',
            },
            'thumbnails': {
                'ENGINE': 'filer.storage.PublicFileSystemStorage',
                'OPTIONS': {
                    'location': '/path/to/media/filer_thumbnails',
                    'base_url': '/smedia/filer_thumbnails/',
                },
            },
        },
        'private': {
            'main': {
                'ENGINE': 'filer.storage.PrivateFileSystemStorage',
                'OPTIONS': {
                    'location': '/path/to/smedia/filer',
                    'base_url': '/smedia/filer/',
                },
                'UPLOAD_TO': 'filer.utils.generate_filename.by_date',
            },
            'thumbnails': {
                'ENGINE': 'filer.storage.PrivateFileSystemStorage',
                'OPTIONS': {
                    'location': '/path/to/smedia/filer_thumbnails',
                    'base_url': '/smedia/filer_thumbnails/',
                },
            },
        },
    }

Defaults to FileSystemStorage in ``<MEDIA_ROOT>/filer/`` and ``<MEDIA_ROOT>/filer_thumbnails/`` for public files and
``<MEDIA_ROOT>/../smedia/filer/`` and ``<MEDIA_ROOT>/../smedia/filer_thumbnails/`` for private files.

``UPLOAD_TO`` is the function to generate the path relative to the storage root. The
default generates a date based path like ``2011/05/03/filename.jpg``. This
will be applied with the current date whenever a file is uploaded or moved
between public (without permission checks) and private (with permission
checks) storages. Defaults to ``'filer.utils.generate_filename.by_date'``


``FILER_SERVERS``
------------------

A dictionary to configure server backends to serve files with permissions.

e.g::

    DEFAULT_FILER_SERVERS = {
        'private': {
            'main': {
                'ENGINE': 'filer.server.backends.default.DefaultServer',
            },
            'thumbnails': {
                'ENGINE': 'filer.server.backends.default.DefaultServer',
            }
        }
    }

Defaults to using the DefaultServer (doh)! This will serve the files with the django app.


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

Defaults to ``False``
