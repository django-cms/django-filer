"""Tests for filer.models.imagemodels — Image.save date_taken logic."""

import os

from django.core.files import File as DjangoFile
from django.test import TestCase

from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from tests.helpers import create_image, create_superuser

Image = load_model(FILER_IMAGE_MODEL)


class ImageSaveTests(TestCase):
    """Tests for Image.save date_taken handling."""

    def setUp(self):
        self.superuser = create_superuser()
        self.img = create_image(mode='RGB', size=(100, 100))
        self.filename = os.path.join('/tmp', 'test_save_image.jpg')
        self.img.save(self.filename, 'JPEG')

    def tearDown(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        for img in Image.objects.all():
            img.delete()

    def test_save_sets_date_taken_to_now_when_no_exif(self):
        with open(self.filename, 'rb') as f:
            file_obj = DjangoFile(f, name='test.jpg')
            image = Image.objects.create(
                owner=self.superuser,
                original_filename='test.jpg',
                file=file_obj,
            )
        self.assertIsNotNone(image.date_taken)

    def test_author_and_copyright_defaults(self):
        with open(self.filename, 'rb') as f:
            file_obj = DjangoFile(f, name='test.jpg')
            image = Image.objects.create(
                owner=self.superuser,
                original_filename='test.jpg',
                file=file_obj,
            )
        self.assertIsNone(image.author)
        self.assertFalse(image.must_always_publish_author_credit)
        self.assertFalse(image.must_always_publish_copyright)
