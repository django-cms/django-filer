import os
import re
from contextlib import contextmanager

from easy_thumbnails.files import Thumbnailer
from easy_thumbnails.namers import default

# easy-thumbnails default pattern
# e.g: source.jpg.100x100_q80_crop_upscale.jpg
RE_ORIGINAL_FILENAME = re.compile(
    r"^(?P<source_filename>.*?)\.(?P<opts_and_ext>[^.]+\.[^.]+)$"
)


def thumbnail_to_original_filename(thumbnail_name):
    m = RE_ORIGINAL_FILENAME.match(thumbnail_name)
    if m:
        return m.group(1)
    return None


@contextmanager
def use_default_namer(thumbnailer):
    """
    Context manager to use the default easy-thumbnails namer for private files.
    """
    original_namer = thumbnailer.thumbnail_namer
    thumbnailer.thumbnail_namer = default
    try:
        yield
    finally:
        thumbnailer.thumbnail_namer = original_namer


class ThumbnailerNameMixin:
    thumbnail_basedir = ""
    thumbnail_subdir = ""
    thumbnail_prefix = ""

    def get_thumbnail_name(self, thumbnail_options, transparent=False):
        """
        Get thumbnail name using easy-thumbnails pattern.
        For public files: Uses configurable naming via THUMBNAIL_NAMER
        For private files: Uses easy-thumbnails default naming pattern regardless of THUMBNAIL_NAMER
        """
        is_public = False
        if hasattr(self, "thumbnail_storage"):
            is_public = "PrivateFileSystemStorage" not in str(
                self.thumbnail_storage.__class__
            )

        if is_public:
            return super(ThumbnailerNameMixin, self).get_thumbnail_name(
                thumbnail_options, transparent
            )

        with use_default_namer(self):
            return super(ThumbnailerNameMixin, self).get_thumbnail_name(
                thumbnail_options, transparent
            )


class ActionThumbnailerMixin:
    thumbnail_basedir = ""
    thumbnail_subdir = ""
    thumbnail_prefix = ""

    def get_thumbnail_name(self, thumbnail_options, transparent=False):
        """
        A version of ``Thumbnailer.get_thumbnail_name`` that returns the original
        filename to resize.
        """
        path, filename = os.path.split(self.name)

        basedir = self.thumbnail_basedir
        subdir = self.thumbnail_subdir

        return os.path.join(basedir, path, subdir, filename)

    def thumbnail_exists(self, thumbnail_name):
        return False


class FilerThumbnailer(ThumbnailerNameMixin, Thumbnailer):
    def __init__(self, *args, **kwargs):
        self.thumbnail_basedir = kwargs.pop("thumbnail_basedir", "")
        super().__init__(*args, **kwargs)


class FilerActionThumbnailer(ActionThumbnailerMixin, Thumbnailer):
    pass
