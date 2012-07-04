#-*- coding: utf-8 -*-
from django.conf import settings
from django.core.files.storage import get_storage_class
from filer.utils.loader import load_object
import os
import urlparse

FILER_ENABLE_PERMISSIONS = getattr(settings, 'FILER_ENABLE_PERMISSIONS', False)

FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS = getattr(settings, 'FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS', False)

FILER_PAGINATE_BY = getattr(settings, 'FILER_PAGINATE_BY', 20)

FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)

FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', True)

FILER_STATICMEDIA_PREFIX = getattr(settings, 'FILER_STATICMEDIA_PREFIX', None)
if not FILER_STATICMEDIA_PREFIX:
    FILER_STATICMEDIA_PREFIX = (getattr(settings, 'STATIC_URL', None) or settings.MEDIA_URL) + 'filer/'

FILER_ADMIN_ICON_SIZES = getattr(settings,"FILER_ADMIN_ICON_SIZES",(
        '16', '32', '48', '64',
))

# This is an ordered iterable that describes a list of 
# classes that I should check for when adding files
FILER_FILE_MODELS = getattr(settings, 'FILER_FILE_MODELS',
    (
        'filer.models.imagemodels.Image',
        'filer.models.filemodels.File',
    )
)

DEFAULT_FILER_STORAGES = {
    'public': {
        'main': {
            'ENGINE': 'filer.storage.PublicFileSystemStorage',
            'OPTIONS': {
                'location': os.path.abspath(os.path.join(settings.MEDIA_ROOT, 'filer/')),
                'base_url': urlparse.urljoin(settings.MEDIA_URL, 'filer/'),
            },
        },
        'thumbnails': {
            'ENGINE': 'filer.storage.PublicFileSystemStorage',
            'OPTIONS': {
                'location': os.path.abspath(os.path.join(settings.MEDIA_ROOT, 'filer_thumbnails/')),
                'base_url': urlparse.urljoin(settings.MEDIA_URL, 'filer_thumbnails/'),
            },
        }
    },
    'private': {
        'main': {
            'ENGINE': 'filer.storage.PublicFileSystemStorage',
            'OPTIONS': {
                'location': os.path.abspath(os.path.join(settings.MEDIA_ROOT, '../smedia/filer')),
                'base_url': '/smedia/filer/',
            },
        },
        'thumbnails': {
            'ENGINE': 'filer.storage.PublicFileSystemStorage',
            'OPTIONS': {
                'location': os.path.abspath(os.path.join(settings.MEDIA_ROOT, '../smedia/filer_thumbnails')),
                'base_url': '/smedia/filer_thumbnails/',
            },
        }
    },
}

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



FILER_STORAGES = getattr(settings, 'FILER_STORAGES', DEFAULT_FILER_STORAGES)
FILER_SERVERS = getattr(settings, 'FILER_SERVERS', DEFAULT_FILER_SERVERS)

# Public media (media accessible without any permission checks)
FILER_PUBLICMEDIA_STORAGE = get_storage_class(FILER_STORAGES['public']['main']['ENGINE'])(**FILER_STORAGES['public']['main'].get('OPTIONS', {}))
FILER_PUBLICMEDIA_UPLOAD_TO = load_object(getattr(settings, 'FILER_PUBLICMEDIA_UPLOAD_TO', 'filer.utils.generate_filename.by_date'))
FILER_PUBLICMEDIA_THUMBNAIL_STORAGE = get_storage_class(FILER_STORAGES['public']['thumbnails']['ENGINE'])(**FILER_STORAGES['public']['thumbnails'].get('OPTIONS',{}))


# Private media (media accessible through permissions checks)
FILER_PRIVATEMEDIA_STORAGE = get_storage_class(FILER_STORAGES['private']['main']['ENGINE'])(**FILER_STORAGES['private']['main'].get('OPTIONS', {}))
FILER_PRIVATEMEDIA_UPLOAD_TO = load_object(getattr(settings, 'FILER_PRIVATEMEDIA_UPLOAD_TO',
                                       'filer.utils.generate_filename.by_date'))
FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE = get_storage_class(FILER_STORAGES['private']['thumbnails']['ENGINE'])(**FILER_STORAGES['private']['thumbnails'].get('OPTIONS', {}))
FILER_PRIVATEMEDIA_SERVER = load_object(FILER_SERVERS['private']['main']['ENGINE'])(**FILER_SERVERS['private']['main'].get('OPTIONS', {}))
FILER_PRIVATEMEDIA_THUMBNAIL_SERVER = load_object(FILER_SERVERS['private']['thumbnails']['ENGINE'])(**FILER_SERVERS['private']['thumbnails'].get('OPTIONS', {}))
