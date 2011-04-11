#-*- coding: utf-8 -*-
import datetime
import os
import urlparse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_unicode, smart_str
from filer.storage import PublicFileSystemStorage, PrivateFileSystemStorage

FILER_PAGINATE_BY = getattr(settings, 'FILER_PAGINATE_BY', 20)

FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)

FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', False)

FILER_STATICMEDIA_PREFIX = getattr(settings, 'FILER_STATICMEDIA_PREFIX', None)
if not FILER_STATICMEDIA_PREFIX:
    FILER_STATICMEDIA_PREFIX = (getattr(settings,'STATIC_URL', None) or settings.MEDIA_URL) + 'filer/'

FILER_ADMIN_ICON_SIZES = (
        '16', '32', '48', '64',
)

# Public Media

FILER_PUBLICMEDIA_ROOT = getattr(settings, 'FILER_PUBLICMEDIA_ROOT',
FILER_PUBLICMEDIA_URL = getattr(settings, 'FILER_PUBLICMEDIA_URL', urlparse.urljoin(settings.MEDIA_URL, 'filer_public/').replace('\\', '/') )
                                 os.path.abspath( os.path.join(settings.MEDIA_ROOT, 'filer_public/' ) ) )
FILER_PUBLICMEDIA_STORAGE = getattr(settings,
                                    'FILER_PUBLICMEDIA_STORAGE',
                                    PublicFileSystemStorage(
                                        location=FILER_PUBLICMEDIA_ROOT,
                                        base_url=FILER_PUBLICMEDIA_URL
                                    ))
FILER_PUBLICMEDIA_UPLOAD_TO = getattr(settings, 'FILER_PUBLICMEDIA_UPLOAD_TO', 'filer.utils.generate_filename.by_date')

FILER_PUBLICMEDIA_THUMBNAIL_ROOT = getattr(settings, 'FILER_PUBLICMEDIA_ROOT',
FILER_PUBLICMEDIA_THUMBNAIL_URL = getattr(settings, 'FILER_PUBLICMEDIA_URL', urlparse.urljoin(settings.MEDIA_URL, 'filer_public/').replace('\\', '/') )
                                 os.path.abspath( os.path.join(settings.MEDIA_ROOT, 'filer_public/' ) ) )
FILER_PUBLICMEDIA_THUMBNAIL_STORAGE = getattr(settings,
                                    'FILER_PUBLICMEDIA_STORAGE',
                                    PublicFileSystemStorage(
                                        location=FILER_PUBLICMEDIA_THUMBNAIL_ROOT,
                                        base_url=FILER_PUBLICMEDIA_THUMBNAIL_URL
                                    ))

# Private Media

FILER_PRIVATEMEDIA_ROOT = getattr(settings, 'FILER_PRIVATEMEDIA_ROOT',
                                  os.path.abspath( os.path.join(settings.MEDIA_ROOT, '../smedia/files/' ) ) )
FILER_PRIVATEMEDIA_URL = getattr(settings, 'FILER_PRIVATEMEDIA_URL',
                                 '/smedia/files/' )
FILER_PRIVATEMEDIA_STORAGE = getattr(settings,
                                    'FILER_PRIVATEMEDIA_STORAGE',
                                    PrivateFileSystemStorage(
                                        location=FILER_PRIVATEMEDIA_ROOT,
                                        base_url=FILER_PRIVATEMEDIA_URL
                                    ))
FILER_PRIVATEMEDIA_UPLOAD_TO = getattr(settings, 'FILER_PRIVATEMEDIA_UPLOAD_TO',
                                       'filer.utils.generate_filename.by_date')
FILER_PRIVATEMEDIA_THUMBNAIL_ROOT = getattr(settings, 'FILER_PRIVATEMEDIA_ROOT',
                                  os.path.abspath( os.path.join(settings.MEDIA_ROOT, '../smedia/files/' ) ) )
FILER_PRIVATEMEDIA_THUMBNAIL_URL = getattr(settings, 'FILER_PRIVATEMEDIA_URL',
                                 '/smedia/files/' )
FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE = getattr(settings,
                                    'FILER_PRIVATEMEDIA_STORAGE',
                                    PrivateFileSystemStorage(
                                        location=FILER_PRIVATEMEDIA_THUMBNAIL_ROOT,
                                        base_url=FILER_PRIVATEMEDIA_THUMBNAIL_URL
                                    ))
FILER_PRIVATEMEDIA_SERVER = getattr(settings, 'FILER_PRIVATEMEDIA_SERVER', "filer.server.backends.default.DefaultServer")

FILER_NGINX_PROTECTED_LOCATION = getattr(settings, 'FILER_NGINX_PROTECTED_LOCATION', "protected_media")

