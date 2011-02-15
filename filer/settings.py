import datetime
import os
import urlparse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_unicode, smart_str
from filer.utils.files import get_valid_filename

def generate_filename(instance, filename):
    datepart = force_unicode(datetime.datetime.now().strftime(smart_str("%Y/%m/%d")))
    return os.path.join(datepart, get_valid_filename(filename))

FILER_PAGINATE_BY = getattr(settings, 'FILER_PAGINATE_BY', 5)

FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)

FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', False)

FILER_STATICMEDIA_PREFIX = getattr(settings, 'FILER_STATICMEDIA_PREFIX', settings.MEDIA_URL + 'filer/' )

FILER_PUBLICMEDIA_PREFIX = getattr(settings, 'FILER_PUBLICMEDIA_PREFIX', 'filer_public/')
FILER_PUBLICMEDIA_URL = getattr(settings, 'FILER_PUBLICMEDIA_URL', urlparse.urljoin(settings.MEDIA_URL, FILER_PUBLICMEDIA_PREFIX).replace('\\', '/') )
FILER_PUBLICMEDIA_ROOT = os.path.abspath( os.path.join(settings.MEDIA_ROOT, FILER_PUBLICMEDIA_PREFIX ) )
FILER_PUBLICMEDIA_STORAGE = getattr(settings,
                                    'FILER_PUBLICMEDIA_STORAGE',
                                    'filer.storage.PublicFileSystemStorage')

FILER_PUBLICMEDIA_UPLOAD_TO = getattr(settings, 'FILER_PUBLICMEDIA_UPLOAD_TO', generate_filename)


FILER_PRIVATEMEDIA_PREFIX = getattr(settings, 'FILER_PRIVATEMEDIA_PREFIX', 'filer_private/')
FILER_PRIVATEMEDIA_URL = getattr(settings, 'FILER_PRIVATEMEDIA_URL', urlparse.urljoin(settings.MEDIA_URL,FILER_PRIVATEMEDIA_PREFIX).replace('\\', '/') )
FILER_PRIVATEMEDIA_ROOT = os.path.abspath( os.path.join(settings.MEDIA_ROOT, FILER_PRIVATEMEDIA_PREFIX ) )
FILER_PRIVATEMEDIA_STORAGE = getattr(settings,
                                    'FILER_PRIVATEMEDIA_STORAGE',
                                    'filer.storage.PrivateFileSystemStorage')
FILER_PRIVATEMEDIA_UPLOAD_TO = getattr(settings, 'FILER_PRIVATEMEDIA_UPLOAD_TO', generate_filename)

if not FILER_PUBLICMEDIA_PREFIX.endswith('/'):
    raise ImproperlyConfigured('FILER_PUBLICMEDIA_PREFIX (currently "%s") must end with a "/"' % FILER_PUBLICMEDIA_PREFIX)
if not FILER_PRIVATEMEDIA_PREFIX.endswith('/'):
    raise ImproperlyConfigured('FILER_PRIVATEMEDIA_PREFIX (currently "%s") must end with a "/"' % FILER_PRIVATEMEDIA_PREFIX)
if not FILER_PUBLICMEDIA_URL.endswith('/'):
    raise ImproperlyConfigured('FILER_PUBLICMEDIA_URL (currently "%s") must end with a "/"' % FILER_PUBLICMEDIA_URL)
if not FILER_PRIVATEMEDIA_URL.endswith('/'):
    raise ImproperlyConfigured('FILER_PRIVATEMEDIA_URL (currently "%s") must end with a "/"' % FILER_PRIVATEMEDIA_URL)

FILER_ADMIN_ICON_SIZES = (
        '16', '32', '48', '64', 
)