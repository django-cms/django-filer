from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename as get_valid_filename_django
from django.template.defaultfilters import slugify
from django.utils.encoding import force_unicode, smart_str
import os
import datetime
from filer import settings as filer_settings
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
        
class PublicFileSystemStorage(FileSystemStorage):
    """
    Public filesystem storage
    """

    def __init__(self, location=None, base_url=None):
        if location is None:
            location = filer_settings.FILER_PUBLICMEDIA_ROOT
        if base_url is None:
            base_url = filer_settings.FILER_PUBLICMEDIA_URL
        self.location = os.path.abspath(location)
        self.base_url = base_url
        
        
class PrivateFileSystemStorage(FileSystemStorage):
    """
    Public filesystem storage
    """

    def __init__(self, location=None, base_url=None):
        if location is None:
            location = filer_settings.FILER_PRIVATEMEDIA_ROOT
        if base_url is None:
            base_url = filer_settings.FILER_PRIVATEMEDIA_URL
        self.location = os.path.abspath(location)
        self.base_url = base_url


def get_directory_name(instance, filename):
    '''
    returns the path relative to the base path (media root
    '''
    datepart = force_unicode(datetime.datetime.now().strftime(smart_str("%Y/%m/%d")))
    return os.path.normpath( os.path.join(instance._file.storage.location,
                                          datepart,
                                          get_valid_filename(filename)) )
    
def move_file():
    pass
