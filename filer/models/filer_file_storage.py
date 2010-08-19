import os
import datetime

from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from django.template.defaultfilters import slugify
from django.utils.encoding import force_unicode, smart_str
from django.utils.importlib import import_module
from django.utils.text import get_valid_filename as get_valid_filename_django

from filer.settings import \
    FILER_UPLOAD_MEDIA_ROOT, FILER_UPLOAD_MEDIA_URL, \
    FILER_FILE_STORAGE, FILER_PUBLICMEDIA_PREFIX, \
    FILER_GET_DIRECTORY_CALLBACK

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

def default_callback(instance, filename):
    url_prefix = FILER_PUBLICMEDIA_PREFIX
    datepart = force_unicode(datetime.datetime.now().strftime(smart_str("%Y/%m/%d")))
    return os.path.normpath( os.path.join(url_prefix, datepart, get_valid_filename(filename)) )

def get_dir_name_callback():
    import_path = FILER_GET_DIRECTORY_CALLBACK
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a module." % import_path)
    module, funcname = import_path[:dot], import_path[dot+1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing module %s: "%s"' % (module, e))
    try:
        return getattr(mod, funcname)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define the callback: "%s".' % (module, funcname))

def get_directory_name(instance, filename):
    '''
    returns the path relative to the base path (media root
    '''
    if instance and instance._file:
        # assigning our storage_class
        storage_class = get_storage_class()
        instance._file.storage = storage_class() # is this too hacky?
    callback = get_dir_name_callback()
    return callback(instance, filename)

def get_storage_class(import_path=None):
    '''
    Copied and modified from django.core.files.storage
    '''
    if import_path is None:
        import_path = FILER_FILE_STORAGE
    try:
        dot = import_path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured("%s isn't a storage module." % import_path)
    module, classname = import_path[:dot], import_path[dot+1:]
    try:
        mod = import_module(module)
    except ImportError, e:
        raise ImproperlyConfigured('Error importing storage module %s: "%s"' % (module, e))
    try:
        return getattr(mod, classname)
    except AttributeError:
        raise ImproperlyConfigured('Storage module "%s" does not define a "%s" class.' % (module, classname))

class FilerFileSystemStorage(FileSystemStorage):
    '''
    The default storage class that is using the settings FILER_UPLOAD_MEDIA_ROOT and 
    FILER_UPLOAD_MEDIA_URL. There you can define where uploads are saved and served from.
    You can also exchange this default storage class through the setting
    FILER_FILE_STORAGE.
    '''
    def __init__(self, location=None, base_url=None):
        super(FilerFileSystemStorage, self).__init__(location, base_url)
        # using the base location & url from the filer settings
        self.location = FILER_UPLOAD_MEDIA_ROOT
        self.base_url = FILER_UPLOAD_MEDIA_URL