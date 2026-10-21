"""Tests for filer.utils.filer_easy_thumbnails."""

from django.test import TestCase

from filer.utils.filer_easy_thumbnails import (
    ThumbnailerNameMixin,
    thumbnail_to_original_filename,
)


class ThumbnailToOriginalFilenameTests(TestCase):
    """Tests for thumbnail_to_original_filename."""

    def test_with_delimiter(self):
        result = thumbnail_to_original_filename('path/to/file.jpg__100x100_q85.jpg')
        self.assertEqual(result, 'path/to/file.jpg')

    def test_without_delimiter(self):
        result = thumbnail_to_original_filename('file.jpg')
        self.assertIsNone(result)

    def test_multiple_delimiters(self):
        # rsplit('__', 1) splits at the LAST occurrence
        result = thumbnail_to_original_filename('a__b__100x100.jpg')
        self.assertEqual(result, 'a__b')


class ThumbnailerNameMixinTests(TestCase):
    """Tests for ThumbnailerNameMixin.get_thumbnail_name."""

    def setUp(self):
        class TestThumbnailer(ThumbnailerNameMixin):
            name = 'uploads/test_image.png'
            thumbnail_quality = 85
            thumbnail_extension = 'jpg'
            thumbnail_transparency_extension = 'png'
            thumbnail_preserve_extensions = False

        self.thumbnailer = TestThumbnailer()

    def test_basic_thumbnail_name(self):
        name = self.thumbnailer.get_thumbnail_name({'size': (100, 100), 'crop': True})
        self.assertIn('test_image.png__100x100', name)
        self.assertIn('q85', name)
        self.assertIn('crop', name)

    def test_svg_preserves_extension(self):
        """SVG source files preserve the SVG extension."""
        class SVGThumbnailer(ThumbnailerNameMixin):
            name = 'uploads/icon.svg'
            thumbnail_quality = 85
            thumbnail_extension = 'jpg'
            thumbnail_transparency_extension = 'png'
            thumbnail_preserve_extensions = False

        thumbnailer = SVGThumbnailer()
        name = thumbnailer.get_thumbnail_name({'size': (50, 50)})
        self.assertTrue(name.endswith('.svg'))

    def test_transparent_preserves_png(self):
        name = self.thumbnailer.get_thumbnail_name(
            {'size': (100, 100)}, transparent=True
        )
        self.assertTrue(name.endswith('.png'))

    def test_preserve_extensions_list(self):
        class PreservingThumbnailer(ThumbnailerNameMixin):
            name = 'uploads/image.png'
            thumbnail_quality = 85
            thumbnail_extension = 'jpg'
            thumbnail_transparency_extension = 'png'
            thumbnail_preserve_extensions = ['png']

        thumbnailer = PreservingThumbnailer()
        name = thumbnailer.get_thumbnail_name({'size': (100, 100)})
        self.assertTrue(name.endswith('.png'))

    def test_subdir_and_prefix(self):
        class PrefixedThumbnailer(ThumbnailerNameMixin):
            name = 'uploads/photo.jpg'
            thumbnail_basedir = 'basedir'
            thumbnail_subdir = 'subdir'
            thumbnail_prefix = ''
            thumbnail_quality = 85
            thumbnail_extension = 'jpg'
            thumbnail_transparency_extension = 'png'
            thumbnail_preserve_extensions = False

        thumbnailer = PrefixedThumbnailer()
        name = thumbnailer.get_thumbnail_name({'size': (100, 100)})
        self.assertTrue(name.startswith('basedir/uploads/subdir/'))

    def test_quality_in_filename_for_jpg(self):
        """JPG output includes quality in filename; non-JPG does not."""
        name = self.thumbnailer.get_thumbnail_name({'size': (100, 100)})
        self.assertIn('q85', name)
