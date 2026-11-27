"""Tests for filer.models.clipboardmodels, thumbnailoptionmodels, and mixins."""

from django.test import TestCase

from filer.models.clipboardmodels import Clipboard, ClipboardItem
from filer.models.filemodels import File
from filer.models.mixins import IconsMixin
from filer.models.thumbnailoptionmodels import ThumbnailOption
from tests.helpers import create_superuser


class ClipboardModelTests(TestCase):
    """Tests for Clipboard and ClipboardItem models."""

    def setUp(self):
        self.user = create_superuser()

    def test_clipboard_str(self):
        clipboard = Clipboard.objects.create(user=self.user)
        result = str(clipboard)
        self.assertIn(str(self.user), result)
        self.assertIn(str(clipboard.id), result)

    def test_clipboarditem_str(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        file_obj = SimpleUploadedFile(
            name='test.txt', content=b'test',
            content_type='text/plain',
        )
        f = File.objects.create(
            owner=self.user, file=file_obj,
            original_filename='test.txt', is_public=True,
        )
        clipboard = Clipboard.objects.create(user=self.user)
        item = ClipboardItem.objects.create(clipboard=clipboard, file=f)
        result = str(item)
        self.assertIn('ClipboardItem object', result)


class ThumbnailOptionModelTests(TestCase):
    """Tests for ThumbnailOption model."""

    def test_str(self):
        opt = ThumbnailOption(name='Test', width=100, height=200)
        result = str(opt)
        self.assertIn('Test', result)
        self.assertIn('100', result)
        self.assertIn('200', result)

    def test_as_dict(self):
        opt = ThumbnailOption(name='Test', width=100, height=200, crop=True, upscale=False)
        result = opt.as_dict
        self.assertEqual(result, {
            'size': (100, 200),
            'width': 100,
            'height': 200,
            'crop': True,
            'upscale': False,
        })

    def test_as_dict_defaults(self):
        opt = ThumbnailOption(name='Test', width=50, height=50)
        result = opt.as_dict
        self.assertEqual(result['crop'], True)
        self.assertEqual(result['upscale'], True)


class IconsMixinTests(TestCase):
    """Tests for IconsMixin."""

    def test_icons_with_no_icon_attribute(self):
        class Obj(IconsMixin):
            pass

        obj = Obj()
        result = obj.icons
        self.assertEqual(result, {})

    def test_icons_with_icon(self):
        class Obj(IconsMixin):
            _icon = 'image'

        obj = Obj()
        result = obj.icons
        from filer.settings import FILER_ADMIN_ICON_SIZES
        self.assertEqual(len(result), len(FILER_ADMIN_ICON_SIZES))
        for size in FILER_ADMIN_ICON_SIZES:
            self.assertIn(size, result)
            self.assertIn(f'image_{size}x{size}.png', result[size])
