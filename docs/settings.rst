.. _settings:

Settings
========

``FILER_ENABLE_PERMISSIONS``
----------------------------

Activate the or not the Permission check on the files and folders before 
displaying them in the admin. When set to ``False`` it gives all the authorization
to staff members based on standard Django model permissions.

Defaults to ``False``

``FILER_IS_PUBLIC_DEFAULT``
---------------------------

Should newly uploaded files have permission checking disabled (be public) by default.

Defaults to ``False`` (new files have permission checking disable, are public)

.. _FILER_STATICMEDIA_PREFIX:

``FILER_STATICMEDIA_PREFIX``
----------------------------

The prefix for static media where filer will look for bundled javascript, css
and images.

Defaults to ``<STATIC_URL>/filer/`` if ``STATIC_URL`` is defined. Otherwise
falls back to ``<MEDIA_URL>/filer/``. It is the URL where the ``static/filer/`` 
directory should be served.

.. _FILER_STORAGES:

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

Defaults to FileSystemStorage in ``<MEDIA_ROOT>/filer_public/`` and ``<MEDIA_ROOT>/filer_public_thumbnails/`` for public files and
``<MEDIA_ROOT>/../smedia/filer_private/`` and ``<MEDIA_ROOT>/../smedia/filer_private_thumbnails/`` for private files.
Public storage uses ``DEFAULT_FILE_STORAGE`` as default storage backend.

``UPLOAD_TO`` is the function to generate the path relative to the storage root. The
default generates a date based path like ``2011/05/03/filename.jpg``. This
will be applied with the current date whenever a file is uploaded or moved
between public (without permission checks) and private (with permission
checks) storages. Defaults to ``'filer.utils.generate_filename.by_date'``


``FILER_SERVERS``
------------------

.. warning:: Server Backends are experimental and the API may change at any time.

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

Defaults to ``20``

``FILER_SUBJECT_LOCATION_IMAGE_DEBUG``
--------------------------------------

Draws a red circle around to point in the image that was used to do the 
subject location aware image cropping.

Defaults to ``False``

``FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS``
-------------------------------------------------

Regular users are not allowed to create new folders at the root level, only
subfolders of already existing folders, unless this setting is set to ``True``.

Defaults to ``False``

``FILER_FOLDER_AFFECTS_URL``
----------------------------

Set this to ``True`` when your ``UPLOAD_TO`` function generates a path that depends on the
folder the file belongs to.

Having this set to ``True`` has certain implications:

* when renaming a file or moving it in and out of the clipboard the file is renamed/move on the
  backend storage as well
* bulk operations such as *Copy selected files and/or folders* or *Move selected files and/or folders*
  are disabled. Reasons for disabling them are: 

  * they might cause requests to timeout due to the fact that copying/moving a large number of files on the storage backend would take a long time
  * in case of failure the database might end up being out of sync with the storage backend

Defaults to ``False``
