import os
from django.conf import settings

FILER_STATICMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_STATICMEDIA_PREFIX', os.path.join(settings.MEDIA_URL,'filer/') ) ) + '/'

# TODO: could be removed in the future
FILER_PUBLICMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_PUBLICMEDIA_PREFIX', 'filer_public') )
FILER_PRIVATEMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_PRIVATEMEDIA_PREFIX', 'filer_private') )

FILER_GET_DIRECTORY_CALLBACK = getattr(settings, 'FILER_GET_DIRECTORY_CALLBACK', 'filer.models.filer_file_storage.default_callback')

FILER_UPLOAD_MEDIA_ROOT = getattr(settings, 'FILER_UPLOAD_MEDIA_ROOT', settings.MEDIA_ROOT)
FILER_UPLOAD_MEDIA_URL = getattr(settings, 'FILER_UPLOAD_MEDIA_URL', settings.MEDIA_URL)
FILER_FILE_STORAGE = getattr(settings, 'FILER_FILE_STORAGE', 'filer.models.filer_file_storage.FilerFileSystemStorage')

FILER_UNZIP_FILES = getattr(settings, 'FILER_UNZIP_FILES', True)
'''
# either relative to MEDIA_ROOT or a full path, for sorl to work it must be inside MEDIA_ROOT
if getattr(settings,'FILER_PUBLICMEDIA_ROOT', '').startswith('/'):
    FILER_PUBLICMEDIA_ROOT = os.path.abspath( getattr(settings,'FILER_PUBLICMEDIA_ROOT') )
else:
    FILER_PUBLICMEDIA_ROOT = os.path.abspath( os.path.join(settings.MEDIA_ROOT, getattr(settings,'FILER_PUBLICMEDIA_ROOT', 'filer_public') ) )

# either relative to MEDIA_URL or a full path
if  getattr(settings,'FILER_PUBLICMEDIA_URL', '').startswith('/'):
    FILER_PUBLICMEDIA_URL  = os.path.normpath( getattr(settings,'FILER_PUBLICMEDIA_URL') )
else:
    FILER_PUBLICMEDIA_URL = os.path.normpath( os.path.join(settings.MEDIA_URL, getattr(settings,'FILER_PUBLICMEDIA_URL', 'filer_public') ) )

# absolute path to private media directory
FILER_PRIVATEMEDIA_PATH = getattr(settings,'FILER_PRIVATEMEDIA_PATH', '')
# there is no definable FILER_PRIVATEMEDIA_URL, because this is defined by urls.py
'''

FILER_ADMIN_ICON_SIZES = (
        '32','48','64',
)
