from django.core.files.storage import FileSystemStorage
from django.template.defaultfilters import slugify
import os

class SafeFilenameFileSystemStorage(FileSystemStorage):
    def get_valid_name(self, name):
        """
        Returns a filename, based on the provided filename, that's suitable for
        use in the target storage system. (slugify)
        """
        s = super(SafeFilenameFileSystemStorage, self).get_valid_name(name)
        filename, ext = os.path.splitext(s)
        filename = slugify(filename)
        ext = slugify(ext)
        return u'%s.%s' % (filename, ext)