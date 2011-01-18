from django.utils.text import get_valid_filename as get_valid_filename_django
from django.template.defaultfilters import slugify
from django.utils.encoding import force_unicode, smart_str
import os
import datetime

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

def get_directory_name(instance, filename):
    datepart = force_unicode(datetime.datetime.now().strftime(smart_str("%Y/%m/%d")))
    return datepart
    
 