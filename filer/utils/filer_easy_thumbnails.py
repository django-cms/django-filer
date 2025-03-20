import os
import re

from easy_thumbnails.files import Thumbnailer

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
            from filer.storage import PrivateFileSystemStorage
            is_public = not isinstance(self.thumbnail_storage, PrivateFileSystemStorage)

        path, source_filename = os.path.split(self.name)
        thumbnail_name = super(ThumbnailerNameMixin, self).get_thumbnail_name(
            thumbnail_options, transparent
        )
        if is_public:
            return thumbnail_name

        base_thumb_name = os.path.basename(thumbnail_name)
        return os.path.join(
            self.thumbnail_basedir,
            path,
            self.thumbnail_subdir,
            f"{source_filename}.{base_thumb_name}",
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
