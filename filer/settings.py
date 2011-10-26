#-*- coding: utf-8 -*-
from django.conf import settings
from filer.server.backends.default import DefaultServer
from filer.storage import PublicFileSystemStorage, PrivateFileSystemStorage
from filer.utils.loader import load_object, storage_factory
import os
import urlparse

FILER_ENABLE_PERMISSIONS = getattr(settings, 'FILER_ENABLE_PERMISSIONS', False)

FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS = getattr(settings, 'FILER_ALLOW_REGULAR_USERS_TO_ADD_ROOT_FOLDERS', False)

FILER_PAGINATE_BY = getattr(settings, 'FILER_PAGINATE_BY', 20)

FILER_SUBJECT_LOCATION_IMAGE_DEBUG = getattr(settings, 'FILER_SUBJECT_LOCATION_IMAGE_DEBUG', False)

FILER_IS_PUBLIC_DEFAULT = getattr(settings, 'FILER_IS_PUBLIC_DEFAULT', True)

FILER_STATICMEDIA_PREFIX = getattr(settings, 'FILER_STATICMEDIA_PREFIX', None)
if not FILER_STATICMEDIA_PREFIX:
    FILER_STATICMEDIA_PREFIX = (getattr(settings, 'STATIC_URL', None) or settings.MEDIA_URL) + 'filer/'

FILER_ADMIN_ICON_SIZES = (
        '16', '32', '48', '64',
)

# This is an ordered iterable that describes a list of 
# classes that I should check for when adding files
FILER_FILE_MODELS = getattr(settings, 'FILER_FILE_MODELS',
    (
        'filer.models.imagemodels.Image',
        'filer.models.videomodels.Video',
        'filer.models.filemodels.File',
    )
)

# Public media (media accessible without any permission checks)
FILER_PUBLICMEDIA_STORAGE = getattr(
                    settings,
                    'FILER_PUBLICMEDIA_STORAGE',
                    storage_factory(
                        klass=PublicFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         'filer')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  'filer/')
                    ))
FILER_PUBLICMEDIA_UPLOAD_TO = load_object(getattr(settings, 'FILER_PUBLICMEDIA_UPLOAD_TO', 'filer.utils.generate_filename.by_date'))
FILER_PUBLICMEDIA_THUMBNAIL_STORAGE = getattr(
                    settings,
                    'FILER_PUBLICMEDIA_THUMBNAIL_STORAGE',
                    storage_factory(
                        klass=PublicFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         'filer_thumbnails')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  'filer_thumbnails/')
                    ))


# Private media (media accessible through permissions checks)
FILER_PRIVATEMEDIA_STORAGE = getattr(
                    settings,
                    'FILER_PRIVATEMEDIA_STORAGE',
                    storage_factory(
                        klass=PrivateFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         '../smedia/filer/')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  '/smedia/filer/')
                    ))
FILER_PRIVATEMEDIA_UPLOAD_TO = load_object(getattr(settings, 'FILER_PRIVATEMEDIA_UPLOAD_TO',
                                       'filer.utils.generate_filename.by_date'))
FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE = getattr(
                    settings,
                   'FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE',
                    storage_factory(
                        klass=PrivateFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         '../smedia/filer_thumbnails/')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  '/smedia/filer_thumbnails/')
                    ))
FILER_PRIVATEMEDIA_SERVER = getattr(settings, 'FILER_PRIVATEMEDIA_SERVER', DefaultServer())
FILER_PRIVATEMEDIA_THUMBNAIL_SERVER = getattr(settings, 'FILER_PRIVATEMEDIA_THUMBNAIL_SERVER', DefaultServer())

FILER_PUBLICMEDIA_FORMATS_STORAGE = getattr(
                    settings,
                    'FILER_PUBLICMEDIA_FORMATS_STORAGE',
                    storage_factory(
                        klass=PublicFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         'filer_formats')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  'filer_formats/')
                    ))
FILER_PRIVATEMEDIA_FORMATS_STORAGE = getattr(
                    settings,
                    'FILER_PRIVATEMEDIA_FORMATS_STORAGE',
                    storage_factory(
                        klass=PrivateFileSystemStorage,
                        location=os.path.abspath(
                            os.path.join(settings.MEDIA_ROOT,
                                         '../smedia/filer_formats/')),
                        base_url=urlparse.urljoin(settings.MEDIA_URL,
                                                  '/smedia/filer_formats/')
                    ))
FILER_PRIVATEMEDIA_FORMATS_SERVER = getattr(settings, 'FILER_PRIVATEMEDIA_FORMATS_SERVER', DefaultServer())

# formats recognized as video file formats (no leading dot)
FILER_SOURCE_VIDEO_FORMATS = ('mp4', 'avi', 'wmv', 'mov', 'mpg')
# formats to convert into (no leading dot)
FILER_VIDEO_FORMATS = ('flv', 'mp4')
# command line for video checking of dimensions
FFMPEG_CHECK_CMD = "ffmpeg -i %(input_file)s"
# command line for video conversion
FFMPEG_CMD = "ffmpeg -i %(input_file)s -y -b 2326k -ar 44100 -ab 224k -ac 2 -f %(format)s -s  %(target_file)s"
# command line for grabbing preview image from video
GRABIMG_CMD = "ffmpeg -y -i %(input_file)s -vframes 1 -ss 00:00:05 -an -vcodec png -f rawvideo -s %(dimensions)s %(target_file)s"