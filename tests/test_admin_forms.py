"""Tests for filer.admin.forms."""

from django.test import TestCase

from filer.admin.forms import CopyFilesAndFoldersForm, RenameFilesForm, ResizeImagesForm


class CopyFilesAndFoldersFormTests(TestCase):
    """Tests for CopyFilesAndFoldersForm."""

    def test_valid_suffix(self):
        form = CopyFilesAndFoldersForm({'suffix': 'copy'})
        self.assertTrue(form.is_valid())

    def test_empty_suffix(self):
        form = CopyFilesAndFoldersForm({'suffix': ''})
        self.assertTrue(form.is_valid())

    def test_invalid_suffix_characters(self):
        form = CopyFilesAndFoldersForm({'suffix': 'bad/name!'})
        self.assertFalse(form.is_valid())
        self.assertIn('suffix', form.errors)

    def test_valid_suffix_is_cleaned(self):
        form = CopyFilesAndFoldersForm({'suffix': 'COPY Me'})
        self.assertFalse(form.is_valid())  # spaces should be stripped and invalid


class RenameFilesFormTests(TestCase):
    """Tests for RenameFilesForm."""

    def test_valid_rename_format(self):
        form = RenameFilesForm({'rename_format': '%(original_filename)s_copy-%(counter)02d'})
        self.assertTrue(form.is_valid())

    def test_invalid_key_in_format(self):
        form = RenameFilesForm({'rename_format': '%(unknown_key)s'})
        self.assertFalse(form.is_valid())
        self.assertIn('rename_format', form.errors)

    def test_invalid_format_exception(self):
        form = RenameFilesForm({'rename_format': '%(original_filename'})  # incomplete
        self.assertFalse(form.is_valid())

    def test_all_valid_format_keys(self):
        format_str = (
            '%(original_filename)s_%(original_basename)s_%(original_extension)s_'
            '%(current_filename)s_%(current_basename)s_%(current_extension)s_'
            '%(current_folder)s_%(counter)d_%(global_counter)d'
        )
        form = RenameFilesForm({'rename_format': format_str})
        self.assertTrue(form.is_valid())


class ResizeImagesFormTests(TestCase):
    """Tests for ResizeImagesForm."""

    def test_valid_with_thumbnail_option(self):
        from filer.models.thumbnailoptionmodels import ThumbnailOption
        opt = ThumbnailOption.objects.create(name='Small', width=100, height=100)
        form = ResizeImagesForm({'thumbnail_option': opt.pk})
        self.assertTrue(form.is_valid())

    def test_valid_with_width_height(self):
        form = ResizeImagesForm({'width': 200, 'height': 150})
        self.assertTrue(form.is_valid())

    def test_invalid_empty(self):
        form = ResizeImagesForm({})
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_valid_with_crop_and_upscale(self):
        form = ResizeImagesForm({
            'width': 200, 'height': 150,
            'crop': True, 'upscale': False,
        })
        self.assertTrue(form.is_valid())
