import os

from django.conf import settings
from django.core.files import File as DjangoFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from filer.models.filemodels import File
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.filer_easy_thumbnails import thumbnail_to_original_filename
from filer.utils.loader import load_model
from tests.helpers import create_image, create_superuser


Image = load_model(FILER_IMAGE_MODEL)


def custom_namer(source_filename, thumbnail_extension, **kwargs):
    return f"custom_prefix_{source_filename}.{thumbnail_extension}"


class ThumbnailNameTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.img = create_image()
        self.image_name = "test_file.jpg"
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, "JPEG")

    def tearDown(self):
        os.remove(self.filename)
        for f in File.objects.all():
            f.delete()

    def create_filer_image(self, is_public=True):
        with open(self.filename, "rb") as f:
            file_obj = DjangoFile(f)
            image = Image.objects.create(
                owner=self.superuser,
                original_filename=self.image_name,
                file=file_obj,
                is_public=is_public,
            )
        return image

    def expected_default_name(self, image):
        return f"{os.path.basename(image.file.name)}.100x100_q85.jpg"

    def test_thumbnailer_class_for_public_files(self):
        image = self.create_filer_image(is_public=True)
        thumbnailer = image.easy_thumbnails_thumbnailer
        name = thumbnailer.get_thumbnail_name({"size": (100, 100)})
        self.assertEqual(os.path.basename(name), self.expected_default_name(image))

    def test_thumbnailer_class_for_private_files(self):
        image = self.create_filer_image(is_public=False)
        thumbnailer = image.easy_thumbnails_thumbnailer
        name = thumbnailer.get_thumbnail_name({"size": (100, 100)})
        self.assertEqual(os.path.basename(name), self.expected_default_name(image))

    @override_settings(THUMBNAIL_NAMER="tests.test_thumbnails.custom_namer")
    def test_thumbnail_custom_namer(self):
        image = self.create_filer_image(is_public=True)
        thumbnailer = image.easy_thumbnails_thumbnailer
        name = thumbnailer.get_thumbnail_name({"size": (100, 100)})
        self.assertEqual(
            name,
            os.path.join(
                image.file.thumbnail_basedir,
                os.path.dirname(image.file.name),
                f"custom_prefix_{os.path.basename(image.file.name)}.jpg",
            ),
        )

    @override_settings(THUMBNAIL_NAMER="tests.test_thumbnails.custom_namer")
    def test_private_thumbnail_ignores_custom_namer(self):
        """Private thumbnail names have to stay reversible into the source name."""
        image = self.create_filer_image(is_public=False)
        thumbnailer = image.easy_thumbnails_thumbnailer
        name = thumbnailer.get_thumbnail_name({"size": (100, 100)})
        self.assertEqual(os.path.basename(name), self.expected_default_name(image))
        self.assertEqual(thumbnail_to_original_filename(name), image.file.name)

    @override_settings(THUMBNAIL_NAMER="tests.test_thumbnails.custom_namer")
    def test_generated_public_thumbnail_uses_custom_namer(self):
        image = self.create_filer_image(is_public=True)
        thumbnail = image.easy_thumbnails_thumbnailer.get_thumbnail({"size": (100, 100)})
        self.assertTrue(os.path.basename(thumbnail.name).startswith("custom_prefix_"))


SVG_FILE = b"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg version="1.1" baseProfile="full" width="50" height="50" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" fill="red" />
</svg>"""


class SvgThumbnailTests(TestCase):
    """SVG thumbnails are written as SVG, so their name has to stay ``.svg``."""

    def setUp(self):
        self.superuser = create_superuser()

    def create_svg_image(self, is_public=True):
        return Image.objects.create(
            owner=self.superuser,
            original_filename="test_file.svg",
            file=SimpleUploadedFile("test_file.svg", SVG_FILE, content_type="image/svg+xml"),
            mime_type="image/svg+xml",
            is_public=is_public,
        )

    def test_svg_thumbnail_is_svg(self):
        image = self.create_svg_image()
        self.addCleanup(image.delete)
        thumbnail = image.easy_thumbnails_thumbnailer.get_thumbnail({"size": (100, 100)})
        self.assertTrue(thumbnail.name.endswith(".svg"), thumbnail.name)
        with thumbnail.storage.open(thumbnail.name) as f:
            self.assertIn(b"<svg", f.read())

    @override_settings(THUMBNAIL_NAMER="tests.test_thumbnails.custom_namer")
    def test_svg_thumbnail_is_svg_with_custom_namer(self):
        image = self.create_svg_image()
        self.addCleanup(image.delete)
        thumbnail = image.easy_thumbnails_thumbnailer.get_thumbnail({"size": (100, 100)})
        self.assertTrue(thumbnail.name.endswith(".svg"), thumbnail.name)

    def test_private_svg_thumbnail_is_svg(self):
        image = self.create_svg_image(is_public=False)
        self.addCleanup(image.delete)
        thumbnail = image.easy_thumbnails_thumbnailer.get_thumbnail({"size": (100, 100)})
        self.assertTrue(thumbnail.name.endswith(".svg"), thumbnail.name)
        self.assertEqual(thumbnail_to_original_filename(thumbnail.name), image.file.name)
