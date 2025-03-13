import os

from django.conf import settings
from django.core.files import File as DjangoFile
from django.test import TestCase, override_settings

from filer.models.filemodels import File
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from tests.helpers import create_image, create_superuser

Image = load_model(FILER_IMAGE_MODEL)


def custom_namer(thumbnailer, **kwargs):
    path, filename = os.path.split(thumbnailer.name)
    return os.path.join(path, f"custom_prefix_{filename}")


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

    def test_thumbnailer_class_for_public_files(self):
        image = self.create_filer_image(is_public=True)
        thumbnailer = image.easy_thumbnails_thumbnailer
        name = thumbnailer.get_thumbnail_name({"size": (100, 100)})
        self.assertNotIn("__", name)

    def test_thumbnailer_class_for_private_files(self):
        image = self.create_filer_image(is_public=False)
        thumbnailer = image.easy_thumbnails_thumbnailer
        name = thumbnailer.get_thumbnail_name({"size": (100, 100)})
        self.assertIn("__", name)

    @override_settings(THUMBNAIL_NAMER="tests.test_thumbnails.custom_namer")
    def test_thumbnail_custom_namer(self):
        image = self.create_filer_image(is_public=True)
        thumbnailer = image.easy_thumbnails_thumbnailer
        name = thumbnailer.get_thumbnail_name({"size": (100, 100)})
        filename = os.path.basename(name)
        self.assertTrue(filename.startswith("custom_prefix_"))
