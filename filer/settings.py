# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import os

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import get_storage_class

from .utils.loader import load_object
from .utils.recursive_dictionary import RecursiveDictionaryWithExcludes

logger = logging.getLogger(__name__)

FILER_IMAGE_MODEL = getattr(settings, 'FILER_IMAGE_MODEL', False)
FILER_DEBUG = getattr(settings, 'FILER_DEBUG', False)  # When True makes
FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)
FILER_WHITESPACE_COLOR = getattr(settings, 'FILER_WHITESPACE_COLOR', '#FFFFFF')

FILER_0_8_COMPATIBILITY_MODE = getattr(settings, 'FILER_0_8_COMPATIBILITY_MODE', False)

FILER_ENABLE_LOGGING = getattr(settings, 'FILER_ENABLE_LOGGING', False)
if FILER_ENABLE_LOGGING:
    FILER_ENABLE_LOGGING = (
        FILER_ENABLE_LOGGING and (getattr(settings, 'LOGGING') and
                                  ('' in settings.LOGGING['loggers'] or
                                   'filer' in settings.LOGGING['loggers'])))

FILER_ENABLE_PERMISSIONS = getattr(settings, 'FILER_ENABLE_PERMISSIONS', False)
FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS = getattr(settings, 'FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS', False)
FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', True)

FILER_PAGINATE_BY = getattr(settings, 'FILER_PAGINATE_BY', 20)

_ICON_SIZES = getattr(settings, 'FILER_ADMIN_ICON_SIZES', ('16', '32', '48', '64'))
if not _ICON_SIZES:
    raise ImproperlyConfigured('Please, configure FILER_ADMIN_ICON_SIZES')
# Reliably sort by integer value, but keep icon size as string.
# (There is some code in the wild that depends on this being strings.)
FILER_ADMIN_ICON_SIZES = [str(i) for i in sorted([int(s) for s in _ICON_SIZES])]

# Filer admin templates have specific icon sizes hardcoded: 32 and 48.
_ESSENTIAL_ICON_SIZES = ('32', '48')
if not all(x in FILER_ADMIN_ICON_SIZES for x in _ESSENTIAL_ICON_SIZES):
    logger.warn(
        "FILER_ADMIN_ICON_SIZES has not all of the essential icon sizes "
        "listed: {}. Some icons might be missing in admin templates.".format(
            _ESSENTIAL_ICON_SIZES))

# This is an ordered iterable that describes a list of
# classes that I should check for when adding files
FILER_FILE_MODELS = getattr(
    settings, 'FILER_FILE_MODELS',
    (FILER_IMAGE_MODEL if FILER_IMAGE_MODEL else 'filer.models.imagemodels.Image',
     'filer.models.filemodels.File'))

DEFAULT_FILE_STORAGE = getattr(settings, 'DEFAULT_FILE_STORAGE', 'django.core.files.storage.FileSystemStorage')

MINIMAL_FILER_STORAGES = {
    'public': {
        'main': {
            'ENGINE': None,
            'OPTIONS': {},
        },
        'thumbnails': {
            'ENGINE': None,
            'OPTIONS': {},
        }
    },
    'private': {
        'main': {
            'ENGINE': None,
            'OPTIONS': {},
        },
        'thumbnails': {
            'ENGINE': None,
            'OPTIONS': {},
        },
    },
}


DEFAULT_FILER_STORAGES = {
    'public': {
        'main': {
            'ENGINE': DEFAULT_FILE_STORAGE,
            'OPTIONS': {},
            'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
            'UPLOAD_TO_PREFIX': 'filer_public',
        },
        'thumbnails': {
            'ENGINE': DEFAULT_FILE_STORAGE,
            'OPTIONS': {},
            'THUMBNAIL_OPTIONS': {
                'base_dir': 'filer_public_thumbnails',
            },
        },
    },
    'private': {
        'main': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': os.path.abspath(os.path.join(settings.MEDIA_ROOT, '../smedia/filer_private')),
                'base_url': '/smedia/filer_private/',
            },
            'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
            'UPLOAD_TO_PREFIX': '',
        },
        'thumbnails': {
            'ENGINE': 'filer.storage.PrivateFileSystemStorage',
            'OPTIONS': {
                'location': os.path.abspath(os.path.join(settings.MEDIA_ROOT, '../smedia/filer_private_thumbnails')),
                'base_url': '/smedia/filer_private_thumbnails/',
            },
            'THUMBNAIL_OPTIONS': {},
        },
    },
}

MINIMAL_FILER_SERVERS = {
    'private': {
        'main': {
            'ENGINE': None,
            'OPTIONS': {},
        },
        'thumbnails': {
            'ENGINE': None,
            'OPTIONS': {},
        },
    },
}

DEFAULT_FILER_SERVERS = {
    'private': {
        'main': {
            'ENGINE': 'filer.server.backends.default.DefaultServer',
            'OPTIONS': {},
        },
        'thumbnails': {
            'ENGINE': 'filer.server.backends.default.DefaultServer',
            'OPTIONS': {},
        },
    },
}

FILER_STORAGES = RecursiveDictionaryWithExcludes(MINIMAL_FILER_STORAGES, rec_excluded_keys=('OPTIONS', 'THUMBNAIL_OPTIONS'))
if FILER_0_8_COMPATIBILITY_MODE:
    user_filer_storages = {
        'public': {
            'main': {
                'ENGINE': DEFAULT_FILE_STORAGE,
                'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                'UPLOAD_TO_PREFIX': getattr(settings, 'FILER_PUBLICMEDIA_PREFIX', 'filer_public'),
            },
            'thumbnails': {
                'ENGINE': DEFAULT_FILE_STORAGE,
                'OPTIONS': {},
                'THUMBNAIL_OPTIONS': {
                    'base_dir': 'filer_public_thumbnails',
                },
            },
        },
        'private': {
            'main': {
                'ENGINE': DEFAULT_FILE_STORAGE,
                'UPLOAD_TO': 'filer.utils.generate_filename.randomized',
                'UPLOAD_TO_PREFIX': getattr(settings, 'FILER_PRIVATEMEDIA_PREFIX', 'filer_private'),
            },
            'thumbnails': {
                'ENGINE': DEFAULT_FILE_STORAGE,
                'OPTIONS': {},
                'THUMBNAIL_OPTIONS': {
                    'base_dir': 'filer_private_thumbnails',
                },
            },
        },
    }
else:
    user_filer_storages = getattr(settings, 'FILER_STORAGES', {})

FILER_STORAGES.rec_update(user_filer_storages)


def update_storage_settings(user_settings, defaults, s, t):
    if not user_settings[s][t]['ENGINE']:
        user_settings[s][t]['ENGINE'] = defaults[s][t]['ENGINE']
        user_settings[s][t]['OPTIONS'] = defaults[s][t]['OPTIONS']
    if t == 'main':
        if 'UPLOAD_TO' not in user_settings[s][t]:
            user_settings[s][t]['UPLOAD_TO'] = defaults[s][t]['UPLOAD_TO']
        if 'UPLOAD_TO_PREFIX' not in user_settings[s][t]:
            user_settings[s][t]['UPLOAD_TO_PREFIX'] = defaults[s][t]['UPLOAD_TO_PREFIX']
    if t == 'thumbnails':
        if 'THUMBNAIL_OPTIONS' not in user_settings[s][t]:
            user_settings[s][t]['THUMBNAIL_OPTIONS'] = defaults[s][t]['THUMBNAIL_OPTIONS']
    return user_settings

update_storage_settings(FILER_STORAGES, DEFAULT_FILER_STORAGES, 'public', 'main')
update_storage_settings(FILER_STORAGES, DEFAULT_FILER_STORAGES, 'public', 'thumbnails')
update_storage_settings(FILER_STORAGES, DEFAULT_FILER_STORAGES, 'private', 'main')
update_storage_settings(FILER_STORAGES, DEFAULT_FILER_STORAGES, 'private', 'thumbnails')

FILER_SERVERS = RecursiveDictionaryWithExcludes(MINIMAL_FILER_SERVERS, rec_excluded_keys=('OPTIONS',))
FILER_SERVERS.rec_update(getattr(settings, 'FILER_SERVERS', {}))


def update_server_settings(settings, defaults, s, t):
    if not settings[s][t]['ENGINE']:
        settings[s][t]['ENGINE'] = defaults[s][t]['ENGINE']
        settings[s][t]['OPTIONS'] = defaults[s][t]['OPTIONS']
    return settings

update_server_settings(FILER_SERVERS, DEFAULT_FILER_SERVERS, 'private', 'main')
update_server_settings(FILER_SERVERS, DEFAULT_FILER_SERVERS, 'private', 'thumbnails')


# Public media (media accessible without any permission checks)
FILER_PUBLICMEDIA_STORAGE = get_storage_class(FILER_STORAGES['public']['main']['ENGINE'])(**FILER_STORAGES['public']['main']['OPTIONS'])
FILER_PUBLICMEDIA_UPLOAD_TO = load_object(FILER_STORAGES['public']['main']['UPLOAD_TO'])
if 'UPLOAD_TO_PREFIX' in FILER_STORAGES['public']['main']:
    FILER_PUBLICMEDIA_UPLOAD_TO = load_object('filer.utils.generate_filename.prefixed_factory')(FILER_PUBLICMEDIA_UPLOAD_TO, FILER_STORAGES['public']['main']['UPLOAD_TO_PREFIX'])
FILER_PUBLICMEDIA_THUMBNAIL_STORAGE = get_storage_class(FILER_STORAGES['public']['thumbnails']['ENGINE'])(**FILER_STORAGES['public']['thumbnails']['OPTIONS'])
FILER_PUBLICMEDIA_THUMBNAIL_OPTIONS = FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']


# Private media (media accessible through permissions checks)
FILER_PRIVATEMEDIA_STORAGE = get_storage_class(FILER_STORAGES['private']['main']['ENGINE'])(**FILER_STORAGES['private']['main']['OPTIONS'])
FILER_PRIVATEMEDIA_UPLOAD_TO = load_object(FILER_STORAGES['private']['main']['UPLOAD_TO'])
if 'UPLOAD_TO_PREFIX' in FILER_STORAGES['private']['main']:
    FILER_PRIVATEMEDIA_UPLOAD_TO = load_object('filer.utils.generate_filename.prefixed_factory')(FILER_PRIVATEMEDIA_UPLOAD_TO, FILER_STORAGES['private']['main']['UPLOAD_TO_PREFIX'])
FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE = get_storage_class(FILER_STORAGES['private']['thumbnails']['ENGINE'])(**FILER_STORAGES['private']['thumbnails']['OPTIONS'])
FILER_PRIVATEMEDIA_THUMBNAIL_OPTIONS = FILER_STORAGES['private']['thumbnails']['THUMBNAIL_OPTIONS']
FILER_PRIVATEMEDIA_SERVER = load_object(FILER_SERVERS['private']['main']['ENGINE'])(**FILER_SERVERS['private']['main']['OPTIONS'])
FILER_PRIVATEMEDIA_THUMBNAIL_SERVER = load_object(FILER_SERVERS['private']['thumbnails']['ENGINE'])(**FILER_SERVERS['private']['thumbnails']['OPTIONS'])

# By default limit number of simultaneous uploads if we are using SQLite
if settings.DATABASES['default']['ENGINE'].endswith('sqlite3'):
    _uploader_connections = 1
else:
    _uploader_connections = 3
FILER_UPLOADER_CONNECTIONS = getattr(
    settings, 'FILER_UPLOADER_CONNECTIONS', _uploader_connections)

FILER_DUMP_PAYLOAD = getattr(settings, 'FILER_DUMP_PAYLOAD', False)  # Whether the filer shall dump the files payload

FILER_CANONICAL_URL = getattr(settings, 'FILER_CANONICAL_URL', 'canonical/')
