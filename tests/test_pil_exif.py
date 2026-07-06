"""Tests for filer.utils.pil_exif."""

from io import BytesIO

from django.test import TestCase

from filer.utils.pil_exif import get_exif, get_exif_for_file, get_subject_location
from tests.helpers import create_image


class GetExifTests(TestCase):
    """Tests for get_exif utility."""

    def test_get_exif_no_exif_data(self):
        """Image with no EXIF metadata returns empty dict."""
        img = create_image(mode='RGB', size=(100, 100))
        result = get_exif(img)
        self.assertEqual(result, {})

    def test_get_exif_with_broken_image(self):
        """A mock object without _getexif returns empty dict."""
        class BrokenImage:
            def _getexif(self):
                raise Exception("No EXIF")
        result = get_exif(BrokenImage())
        self.assertEqual(result, {})

    def test_get_exif_with_none_exif(self):
        """An object where _getexif returns None."""
        class NoExifImage:
            def _getexif(self):
                return None
        result = get_exif(NoExifImage())
        self.assertEqual(result, {})


class GetExifForFileTests(TestCase):
    """Tests for get_exif_for_file."""

    def test_get_exif_for_file(self):
        """Test extracting EXIF data from a saved file."""
        img = create_image(mode='RGB', size=(100, 100))
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)

        from django.core.files import File as DjangoFile
        from filer.models import File

        # Need to save as a filer File for the storage path
        filer_file = File.objects.create(
            file=DjangoFile(buffer, name='exif_test.jpg'),
            original_filename='exif_test.jpg',
            is_public=True,
        )
        try:
            result = get_exif_for_file(filer_file.file)
            # Non-EXIF JPEG may return empty but should not raise
            self.assertIsInstance(result, dict)
        finally:
            filer_file.delete()


class GetSubjectLocationTests(TestCase):
    """Tests for get_subject_location."""

    def test_with_subject_location(self):
        exif_data = {'SubjectLocation': (400, 300)}
        result = get_subject_location(exif_data)
        self.assertEqual(result, (400, 300))

    def test_without_subject_location(self):
        exif_data = {'OtherKey': 'value'}
        result = get_subject_location(exif_data)
        self.assertIsNone(result)

    def test_empty_exif(self):
        result = get_subject_location({})
        self.assertIsNone(result)
