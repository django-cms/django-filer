import os
from django.conf import settings

FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)

FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', False)

FILER_STATICMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_STATICMEDIA_PREFIX', os.path.join(settings.MEDIA_URL,'filer/') ) ) + '/'

FILER_PUBLICMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_PUBLICMEDIA_PREFIX', 'filer_public') )
FILER_PRIVATEMEDIA_PREFIX = os.path.normpath( getattr(settings, 'FILER_PRIVATEMEDIA_PREFIX', 'filer_private') )

# please don't change these in settings for now. all media dirs must be beneath MEDIA_ROOT!
FILER_PUBLICMEDIA_URL = os.path.normpath( getattr(settings, 'FILER_PUBLICMEDIA_URL', os.path.join(settings.MEDIA_URL,FILER_PUBLICMEDIA_PREFIX) ) )
FILER_PUBLICMEDIA_ROOT = os.path.abspath( os.path.join(settings.MEDIA_ROOT, FILER_PUBLICMEDIA_PREFIX ) )

FILER_PRIVATEMEDIA_URL = os.path.normpath( getattr(settings, 'FILER_PRIVATEMEDIA_URL', os.path.join(settings.MEDIA_URL,FILER_PRIVATEMEDIA_PREFIX) ) )
FILER_PRIVATEMEDIA_ROOT = os.path.abspath( os.path.join(settings.MEDIA_ROOT, FILER_PRIVATEMEDIA_PREFIX ) )


FILER_ADMIN_ICON_SIZES = (
        '16', '32', '48', '64', 
)

FILER_PRIVATEMEDIA_SERVER = getattr(settings, 'FILER_PRIVATEMEDIA_SERVER', "filer.server.UnprotectedServer")

static_server = None
if static_server == None:
   klass = FILER_PRIVATEMEDIA_SERVER
   if klass != None:
       if type(klass) == type(""):
           try:
               module = klass.split('.')
               if len(module) > 1: module = module[:-1]
               module = '.'.join(module)
               exec "import %s" % module
               exec "static_server = %s()" % klass
               #print static_server
           except:
               #print "Failed to create an instance of '%s'" % klass
               static_server = None
               pass
       else: static_server = klass

   if static_server == None:
      #print "FILER: NO STATIC SERVER FOR PRIVATE FILES CONFIGURED. FILES ARE NOT PROTECTED."
      pass
