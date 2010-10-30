from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename as get_valid_filename_django
from django.template.defaultfilters import slugify
from django.utils.encoding import force_unicode, smart_str
import os
import datetime
from filer.settings import FILER_PUBLICMEDIA_PREFIX, FILER_PRIVATEMEDIA_PREFIX
from django.core.exceptions import ImproperlyConfigured

def get_valid_filename(s):
    '''
    like the regular get_valid_filename, but also slugifies away
    umlauts and stuff.
    '''
    s = get_valid_filename_django(s)
    filename, ext = os.path.splitext(s)
    filename = slugify(filename)
    ext = slugify(ext)
    if ext:
        return u"%s.%s" % (filename, ext)
    else:
        return u"%s" % (filename,)

# TODO: public/private media is going to change with a custom FileField and Storate
#       class that supports files that are not in MEDIA_ROOT
def get_directory_name(instance, filename):
    '''
    returns the path relative to the base path (media root
    '''
    datepart = force_unicode(datetime.datetime.now().strftime(smart_str("%Y/%m/%d")))
    if instance.is_public:
        private_or_public = FILER_PUBLICMEDIA_PREFIX
    else:
        private_or_public = FILER_PRIVATEMEDIA_PREFIX
    return os.path.normpath( os.path.join(private_or_public, datepart, get_valid_filename(filename)) )
    
    
    
 