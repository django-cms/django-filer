#-*- coding: utf-8 -*-
import urlparse
from django.core.files.storage import FileSystemStorage

class PublicFileSystemStorage(FileSystemStorage):
    """
    File system storage that saves its files in the filer public directory

    See ``filer.settings`` for the defaults for ``location`` and ``base_url``.
    """
    name = "World Readable"
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        from filer import settings as filer_settings
        location = location or getattr(filer_settings, 'FILER_PUBLICMEDIA_ROOT', None)
        base_url = base_url or getattr(filer_settings, 'FILER_PUBLICMEDIA_URL', None)
        super(PublicFileSystemStorage, self).__init__(location, base_url,
                                                         *args, **kwargs)

class PrivateFileSystemStorage(FileSystemStorage):
    """
    File system storage that saves its files in the filer private directory.
    This directory should NOT be served directly by the web server.

    See ``filer.settings`` for the defaults for ``location`` and ``base_url``.
    """
    is_secure = True
    name = "Secure Filesystem Storage"
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        from filer import settings as filer_settings
        location = location or getattr(filer_settings, 'FILER_PRIVATEMEDIA_ROOT', None)
        base_url = base_url or getattr(filer_settings, 'FILER_PRIVATEMEDIA_URL', None)
        super(PrivateFileSystemStorage, self).__init__(location, base_url,
                                                         *args, **kwargs)
    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        return urlparse.urljoin(self.base_url, name).replace('\\', '/')