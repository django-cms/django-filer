#-*- coding: utf-8 -*-
from easy_thumbnails.files import Thumbnailer
import os
import re
from filer import settings as filer_settings

# match the source filename using `__` as the seperator. ``opts_and_ext`` is non
# greedy so it should match the last occurence of `__`.
# in ``ThumbnailerNameMixin.get_thumbnail_name`` we ensure that there is no `__`
# in the opts part.
RE_ORIGINAL_FILENAME = re.compile(r"^(?P<source_filename>.*)__(?P<opts_and_ext>.*?)$")


def thumbnail_to_original_filename(thumbnail_name):
    m = RE_ORIGINAL_FILENAME.match(thumbnail_name)
    if m:
        return m.group(1)
    return None


class ThumbnailerNameMixin(object):
    thumbnail_basedir = ''
    thumbnail_subdir = ''
    thumbnail_prefix = ''

    def get_thumbnail_name(self, thumbnail_options, transparent=False):
        """
        A version of ``Thumbnailer.get_thumbnail_name`` that produces a
        reproducible thumbnail name that can be converted back to the original
        filename.
        """
        path, source_filename = os.path.split(self.name)
        if transparent:
            extension = self.thumbnail_transparency_extension
        else:
            extension = self.thumbnail_extension
        extension = extension or 'jpg'

        thumbnail_options = thumbnail_options.copy()
        size = tuple(thumbnail_options.pop('size'))
        quality = thumbnail_options.pop('quality', self.thumbnail_quality)
        initial_opts = ['%sx%s' % size, 'q%s' % quality]

        opts = thumbnail_options.items()
        opts.sort()   # Sort the options so the file name is consistent.
        opts = ['%s' % (v is not True and '%s-%s' % (k, v) or k)
                for k, v in opts if v]

        all_opts = '_'.join(initial_opts + opts)

        basedir = self.thumbnail_basedir
        subdir = self.thumbnail_subdir

        #make sure our magic delimiter is not used in all_opts
        all_opts = all_opts.replace('__', '_')
        filename = u'%s__%s.%s' % (source_filename, all_opts, extension)

        return os.path.join(basedir, path, subdir, filename)


class ActionThumbnailerMixin(object):
    thumbnail_basedir = ''
    thumbnail_subdir = ''
    thumbnail_prefix = ''

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
        self.thumbnail_basedir = kwargs.pop('thumbnail_basedir', '')
        super(FilerThumbnailer, self).__init__(*args, **kwargs)


class FilerActionThumbnailer(ActionThumbnailerMixin, Thumbnailer):
    pass
