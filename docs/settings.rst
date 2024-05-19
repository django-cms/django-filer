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

Defaults to ``True`` (new files have permission checking disable, are public)

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
                    'base_url': '/media/filer/',
                },
                'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                'UPLOAD_TO_PREFIX': 'filer_public',
            },
            'thumbnails': {
                'ENGINE': 'filer.storage.PublicFileSystemStorage',
                'OPTIONS': {
                    'location': '/path/to/media/filer_thumbnails',
                    'base_url': '/media/filer_thumbnails/',
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
Public storage uses the default storage's backend. This is taken from Django's ``STORAGES``
setting if it exists or, if not, from the ``DEFAULT_FILE_STORAGE`` setting for compatibility
with earlier Django versions (5.0 or below).

``UPLOAD_TO`` is the function to generate the path relative to the storage root. The
default generates a random path like ``1d/a5/1da50fee-5003-46a1-a191-b547125053a8/filename.jpg``. This
will be applied whenever a file is uploaded or moved between public (without permission checks) and
private (with permission checks) storages. Defaults to ``'filer.utils.generate_filename.randomized'``.

Overriding single keys is possible, for example just set your custom ``UPLOAD_TO``::

    FILER_STORAGES = {
        'public': {
            'main': {
                'UPLOAD_TO': 'my_package.generate_filer_filename.no_dirs',
            },
        },
        # same for private, or not
    }


``FILER_SERVERS``
-----------------

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

Defaults to ``100``

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


``FILER_CANONICAL_URL``
-----------------------

Defines the path element common to all canonical file URLs.

Defaults to ``'canonical/'``


``FILER_UPLOADER_MAX_FILES``
----------------------------

Limit of files to upload by one drag and drop event. This is to avoid
extensive accidental uploads, e.g. by dragging to root direcory onto an
upload field.

Defaults to ``100``.

``FILER_UPLOADER_CONNECTIONS``
------------------------------

Number of simultaneous AJAX uploads. Defaults to 3.

If your database backend is SQLite it would be set to 1 by default. This allows
to avoid ``database is locked`` errors on SQLite during multiple simultaneous
file uploads.

``FILER_UPLOADER_MAX_FILE_SIZE``
--------------------------------

Limits the maximal file size if set. Takes an integer (file size in MB).

Defaults to ``None``.

``FILER_MAX_IMAGE_PIXELS``
--------------------------------

Limits the maximal pixel size of the image that can be uploaded to the Filer.
It will also be lower than or equals to the MAX_IMAGE_PIXELS that Pillow's PIL allows.


``MAX_IMAGE_PIXELS = int(1024 * 1024 * 1024 // 4 // 3)``

Defaults to ``MAX_IMAGE_PIXELS``. But when set, should always be lower than the MAX_IMAGE_PIXELS limit set by Pillow.

This is useful setting to prevent decompression bomb DOS attack.


``FILER_ADD_FILE_VALIDATORS``
-----------------------------

Dictionary that adds file upload validators for specific mime types.
See :ref:`validation`.

``FILER_REMOVE_FILE_VALIDATORS``
--------------------------------

List of default file validators to be ignored.
See :ref:`validation`.
