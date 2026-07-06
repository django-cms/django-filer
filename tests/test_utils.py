import mimetypes
import os
from unittest.mock import MagicMock
from zipfile import ZipFile

from django.conf import settings
from django.core.files import File as DjangoFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from filer.settings import IMAGE_EXTENSIONS
from filer.utils.filer_easy_thumbnails import thumbnail_to_original_filename
from filer.utils.files import (
    UploadException,
    get_valid_filename,
    handle_request_files_upload,
    slugify,
)
from filer.utils.loader import load_object
from filer.utils.zip import unzip
from tests.helpers import create_image


# Some target classes for the classloading tests
class TestTargetSuperClass:
    pass


class TestTargetClass(TestTargetSuperClass):
    pass


# Testing the classloader
class ClassLoaderTestCase(TestCase):
    ''' Tests filer.utils.loader.load() '''

    def test_loader_loads_strings_properly(self):
        target = 'tests.test_utils.TestTargetClass'
        result = load_object(target)
        self.assertEqual(result, TestTargetClass)

    def test_loader_loads_class(self):
        result = load_object(TestTargetClass())
        self.assertEqual(result.__class__, TestTargetClass)

    def test_loader_loads_subclass(self):
        result = load_object(TestTargetClass)
        self.assertEqual(result, TestTargetClass)


# Testing the zipping/unzipping of files
class ZippingTestCase(TestCase):

    def setUp(self):
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename, 'rb'), name=self.image_name)

        self.zipfilename = 'test_zip.zip'

        self.zip = ZipFile(self.zipfilename, 'a')
        self.zip.write(self.filename)
        self.zip.close()

    def tearDown(self):
        if os.path.exists(self.zipfilename):
            os.remove(self.zipfilename)
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def test_unzipping_works(self):
        result = unzip(self.zipfilename)
        self.assertEqual(result[0][0].name, self.file.name)


class MimeTypesTestCase(TestCase):
    def test_mime_types_known(self):
        """Ensure that for all IMAGE_EXTENSIONS the MIME types can be identified"""
        for ext in IMAGE_EXTENSIONS:
            self.assertIsNotNone(mimetypes.guess_type(f"file{ext}")[0],
                                 f"Mime type for extension {ext} unknown")


class ThumbnailToOriginalFilenameTestCase(TestCase):
    def test_no_separator_returns_none(self):
        self.assertIsNone(thumbnail_to_original_filename("foo.jpg"))

    def test_normal_thumbnail_name(self):
        self.assertEqual(
            thumbnail_to_original_filename("foo.jpg__200x200_q85.jpg"),
            "foo.jpg",
        )

    def test_multiple_separators_returns_part_before_last(self):
        self.assertEqual(
            thumbnail_to_original_filename("a__b.jpg__200x200.jpg"),
            "a__b.jpg",
        )

    def test_leading_separator_returns_empty_string(self):
        self.assertEqual(
            thumbnail_to_original_filename("__opts.jpg"),
            "",
        )


# ---- New tests for filer.utils.files utilities ----


class GetValidFilenameTests(TestCase):
    """Tests for get_valid_filename."""

    def test_simple_filename(self):
        result = get_valid_filename('hello world.txt')
        self.assertNotIn(' ', result)
        self.assertTrue(result.endswith('.txt'))

    def test_umlauts_slugified(self):
        result = get_valid_filename('über file.txt')
        self.assertIn('uber', result)
        self.assertNotIn('ü', result)

    def test_no_extension(self):
        result = get_valid_filename('hello_world')
        self.assertNotIn('.', result)

    def test_special_characters(self):
        result = get_valid_filename('my (file) #1.txt')
        self.assertNotIn('(', result)
        self.assertNotIn(')', result)
        self.assertNotIn('#', result)

    def test_long_filename_truncated(self):
        long_name = 'a' * 200 + '.txt'
        result = get_valid_filename(long_name)
        # Truncation may drop the extension; just verify length is safe
        self.assertLessEqual(len(result), 155)


class SlugifyTests(TestCase):
    """Tests for slugify."""

    def test_slugify_basic(self):
        result = slugify('Hello World')
        self.assertEqual(result, 'hello-world')

    def test_slugify_umlaut(self):
        result = slugify('über cool')
        self.assertIn('uber', result)


class HandleRequestFilesUploadTests(TestCase):
    """Tests for handle_request_files_upload."""

    def test_single_file(self):
        upload = SimpleUploadedFile('test.txt', b'hello', content_type='text/plain')

        # Simulate request.FILES as a dict-like with a single entry
        class FakeFiles(dict):
            pass

        request = MagicMock()
        fake_files = FakeFiles({'file': upload})
        request.FILES = fake_files

        result = handle_request_files_upload(request)
        self.assertEqual(result[1], 'test.txt')
        self.assertEqual(result[3], 'text/plain')
        self.assertFalse(result[2])  # is_raw is False

    def test_mime_type_mismatch_raises(self):
        """Uploading a file with mismatched MIME type and extension raises."""
        upload = SimpleUploadedFile('test.txt', b'<html>content</html>', content_type='text/html')

        class FakeFiles(dict):
            pass

        request = MagicMock()
        request.FILES = FakeFiles({'file': upload})

        with self.assertRaises(UploadException):
            handle_request_files_upload(request)


class UploadExceptionTests(TestCase):
    """Tests for UploadException."""

    def test_upload_exception(self):
        exc = UploadException('test error')
        self.assertEqual(str(exc), 'test error')
        self.assertIsInstance(exc, Exception)
