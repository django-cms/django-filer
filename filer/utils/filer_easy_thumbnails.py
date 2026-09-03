import os
from io import StringIO

from django.core.files.base import ContentFile

from easy_thumbnails import engine, utils
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import Thumbnailer, ThumbnailFile

from . import svg


def thumbnail_to_original_filename(thumbnail_name):
    if '__' not in thumbnail_name:
        return None
    return thumbnail_name.rsplit('__', 1)[0]


class ThumbnailerNameMixin:
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
        source_extension = os.path.splitext(source_filename)[1][1:].lower()
        preserve_extensions = self.thumbnail_preserve_extensions
        if preserve_extensions is True or source_extension == 'svg' or \
                isinstance(preserve_extensions, (list, tuple)) and source_extension in preserve_extensions:
            extension = source_extension
        elif transparent:
            extension = self.thumbnail_transparency_extension
        else:
            extension = self.thumbnail_extension
        extension = extension or 'jpg'

        thumbnail_options = thumbnail_options.copy()
        size = tuple(thumbnail_options.pop('size'))
        initial_opts = ['{}x{}'.format(*size)]
        quality = thumbnail_options.pop('quality', self.thumbnail_quality)
        if extension == 'jpg':
            initial_opts.append(f'q{quality}')
        elif extension == 'svg':
            thumbnail_options.pop('subsampling', None)
            thumbnail_options.pop('upscale', None)

        opts = list(thumbnail_options.items())
        opts.sort()   # Sort the options so the file name is consistent.
        opts = ['{}'.format(v is not True and f'{k}-{v}' or k)
                for k, v in opts if v]
        all_opts = '_'.join(initial_opts + opts)

        basedir = self.thumbnail_basedir
        subdir = self.thumbnail_subdir

        # make sure our magic delimiter is not used in all_opts
        all_opts = all_opts.replace('__', '_')
        filename = f'{source_filename}__{all_opts}.{extension}'

        return os.path.join(basedir, path, subdir, filename)


class ActionThumbnailerMixin:
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


def svg_source_generator(source, **options):
    """
    An easy-thumbnails source generator that opens an SVG with
    :mod:`filer.utils.svg` instead of ``easy_thumbnails.VIL``, so that
    thumbnailing an SVG needs no SVG renderer.
    """
    if not source:
        return None
    return svg.load(source)


class SvgThumbnailFile(ThumbnailFile):
    """
    A ``ThumbnailFile`` that reads the dimensions of an SVG thumbnail from the
    document itself. easy-thumbnails resolves them through
    ``easy_thumbnails.VIL``, which requires svglib and reportlab.
    """

    def _get_image_dimensions(self):
        if not hasattr(self, '_dimensions_cache'):
            close = self.closed
            self.open()
            try:
                self._dimensions_cache = svg.get_dimensions(self)
            finally:
                if close:
                    self.close()
        return self._dimensions_cache


class SvgThumbnailerMixin:
    """
    Thumbnail SVG sources by rewriting the document instead of rendering it.

    Scaling and cropping an SVG only means setting ``width``, ``height`` and
    ``viewBox`` on the root element, which keeps the original vector data
    intact. easy-thumbnails does the same thing, but reaches the root element
    by parsing the file with svglib and re-drawing it onto a reportlab canvas
    -- an optional dependency of filer since 3.6.
    """

    def generate_thumbnail(self, thumbnail_options, silent_template_exception=False):
        if not svg.is_svg(self.name):
            return super().generate_thumbnail(
                thumbnail_options,
                silent_template_exception=silent_template_exception)

        thumbnail_options = self.get_options(thumbnail_options)
        image = engine.generate_source_image(
            self, thumbnail_options, [svg_source_generator],
            fail_silently=silent_template_exception)
        if image is None:
            msg = "The source file does not appear to be an SVG image: '{name}'"
            raise InvalidImageFormatError(msg.format(name=self.name))

        thumbnail_image = engine.process_image(
            image, thumbnail_options, self.thumbnail_processors)
        filename = self.get_thumbnail_name(
            thumbnail_options,
            transparent=utils.is_transparent(thumbnail_image))

        destination = StringIO()
        thumbnail_image.save(destination, format='SVG')

        thumbnail = SvgThumbnailFile(
            filename, file=ContentFile(destination.getvalue().encode()),
            storage=self.thumbnail_storage, thumbnail_options=thumbnail_options)
        thumbnail.image = thumbnail_image
        thumbnail._committed = False
        thumbnail._dimensions_cache = thumbnail_image.size
        return thumbnail

    def get_existing_thumbnail(self, thumbnail_options):
        thumbnail = super().get_existing_thumbnail(thumbnail_options)
        if thumbnail is not None and svg.is_svg(thumbnail.name):
            # easy-thumbnails builds the ``ThumbnailFile`` deep inside
            # ``get_existing_thumbnail()`` and offers no hook for the class it
            # uses. Re-tagging the instance is the least invasive way to give
            # SVG thumbnails dimensions without svglib.
            thumbnail.__class__ = SvgThumbnailFile
        return thumbnail


class FilerThumbnailer(SvgThumbnailerMixin, ThumbnailerNameMixin, Thumbnailer):
    def __init__(self, *args, **kwargs):
        self.thumbnail_basedir = kwargs.pop('thumbnail_basedir', '')
        super().__init__(*args, **kwargs)


class FilerActionThumbnailer(SvgThumbnailerMixin, ActionThumbnailerMixin, Thumbnailer):
    pass
