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
                'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                'UPLOAD_TO_PREFIX': 'filer_public',
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
                'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                'UPLOAD_TO_PREFIX': 'filer_public',
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
default generates a random path like ``1d/a5/1da50fee-5003-46a1-a191-b547125053a8/filename.jpg``. This
will be applied whenever a file is uploaded or moved between public (without permission checks) and 
private (with permission checks) storages. Defaults to ``'filer.utils.generate_filename.randomized'``.


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


``FILER_IMAGE_MODEL``
---------------------

Defines the dotted path to a custom Image model; please include the model name.
Example: 'my.app.models.CustomImage'

Defaults to ``False``