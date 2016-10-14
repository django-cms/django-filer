#-*- coding: utf-8 -*-
import os

from django.conf import settings
from django.core.files.storage import get_storage_class

from filer.utils.loader import load_object
from filer.utils.recursive_dictionary import RecursiveDictionaryWithExcludes


FILER_DEBUG = getattr(settings, 'FILER_DEBUG', False) # When True makes
FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)

FILER_0_8_COMPATIBILITY_MODE = getattr(settings, 'FILER_0_8_COMPATIBILITY_MODE', False)

FILER_ENABLE_LOGGING = getattr(settings, 'FILER_ENABLE_LOGGING', False)
if FILER_ENABLE_LOGGING:
    FILER_ENABLE_LOGGING = (FILER_ENABLE_LOGGING and (getattr(settings, 'LOGGING') and
                                                      ('' in settings.LOGGING['loggers'] or
                                                       'filer' in settings.LOGGING['loggers'])))

FILER_ENABLE_PERMISSIONS = getattr(settings, 'FILER_ENABLE_PERMISSIONS', False)
FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', True)

FILER_PAGINATE_BY = getattr(settings, 'FILER_PAGINATE_BY', 20)
FILER_STATICMEDIA_PREFIX = getattr(settings, 'FILER_STATICMEDIA_PREFIX', None)
if not FILER_STATICMEDIA_PREFIX:
    FILER_STATICMEDIA_PREFIX = (getattr(settings, 'STATIC_URL', None) or settings.MEDIA_URL) + 'filer/'

FILER_ADMIN_ICON_SIZES = getattr(settings, "FILER_ADMIN_ICON_SIZES", ('32',))

# This is an ordered iterable that describes a list of
# classes that I should check for when adding files
FILER_FILE_MODELS = getattr(settings, 'FILER_FILE_MODELS',
    (
        'filer.models.imagemodels.Image',
        'filer.models.archivemodels.Archive',
        'filer.models.filemodels.File',
    )
)

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
            'UPLOAD_TO': 'filer.utils.generate_filename.by_date',
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
            'UPLOAD_TO': 'filer.utils.generate_filename.by_date',
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
                'UPLOAD_TO': 'filer.utils.generate_filename.by_date',
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
                'UPLOAD_TO': 'filer.utils.generate_filename.by_date',
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
        if not 'UPLOAD_TO' in user_settings[s][t]:
            user_settings[s][t]['UPLOAD_TO'] = defaults[s][t]['UPLOAD_TO']
        if not 'UPLOAD_TO_PREFIX' in user_settings[s][t]:
            user_settings[s][t]['UPLOAD_TO_PREFIX'] = defaults[s][t]['UPLOAD_TO_PREFIX']
    if t == 'thumbnails':
        if not 'THUMBNAIL_OPTIONS' in user_settings[s][t]:
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

FOLDER_AFFECTS_URL = getattr(settings, 'FILER_FOLDER_AFFECTS_URL', False)
CDN_DOMAIN = getattr(settings, 'FILER_CDN_DOMAIN', None)
CDN_INVALIDATION_TIME = getattr(settings, 'FILER_CDN_INVALIDATION_TIME', 0)
FILER_TRASH_PREFIX = getattr(settings, 'FILER_TRASH_PREFIX', '_trash')
# defaults to one day
FILER_TRASH_CLEAN_INTERVAL = getattr(settings, 'FILER_TRASH_CLEAN_INTERVAL', 60 * 60 * 24)


# Roles Manager that controles how the filer checks permissions
# Must be a callable or a the absolute path of the callable as a string.
# Calling this manager should return an object that must define these functions:
#
# def is_site_admin(user):
#     """
#     :param user: django.contrib.auth.models.User to check permissions for
#     :return: True if the user is an admin on any site, False otherwise
#     """
#     pass

# def has_perm_on_site(user, site_id, perm):
#     """
#     :param user: django.contrib.auth.models.User to check permissions for
#     :param site_id: id of django.contrib.sites.models.Site
#                     on which the user must have the permission
#     :param perm: full name (<app_label>.<permission>) of the permission, ex: filer.add_file
#     :return: True if the user has the permission on that site, False otherwise
#     """
#     pass

# def get_accessible_sites(user):
#     """
#     :return: list of django.contrib.sites.models.Site IDs on which the user has access.
#     """
#     pass

# def get_administered_sites(user):
#     """
#     :return: list of django.contrib.sites.models.Site objects on which the user has admin access.
#     """
#     pass

FILER_ROLES_MANAGER = getattr(settings,
                              'FILER_ROLES_MANAGER',
                              'cmsroles.siteadmin.FilerRolesManager')
