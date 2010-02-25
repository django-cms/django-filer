import os
from django.conf import settings

FILER_STATICMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_STATICMEDIA_PREFIX', os.path.join(settings.MEDIA_URL,'filer/') ) ) + '/'


FILER_PUBLICMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_PUBLICMEDIA_PREFIX', 'filer_public') )
FILER_PRIVATEMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_PRIVATEMEDIA_PREFIX', 'filer_private') )

# please don't change these in settings for now. all media dirs must be beneath MEDIA_ROOT!
FILER_PUBLICMEDIA_URL = os.path.normpath( getattr(settings, 'FILER_PUBLICMEDIA_URL', os.path.join(settings.MEDIA_URL,FILER_PUBLICMEDIA_PREFIX) ) )
FILER_PUBLICMEDIA_ROOT = os.path.abspath( os.path.join(settings.MEDIA_ROOT, FILER_PUBLICMEDIA_PREFIX ) )

FILER_PRIVATEMEDIA_URL = os.path.normpath( getattr(settings, 'FILER_PRIVATEMEDIA_URL', os.path.join(settings.MEDIA_URL,FILER_PRIVATEMEDIA_PREFIX) ) )
FILER_PRIVATEMEDIA_ROOT = os.path.abspath( os.path.join(settings.MEDIA_ROOT, FILER_PRIVATEMEDIA_PREFIX ) )

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