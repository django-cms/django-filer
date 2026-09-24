import os
import shutil
import tempfile
from io import BytesIO, StringIO

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase

from filer.models.filemodels import File
from filer.models.foldermodels import Folder
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from tests.helpers import create_image


Image = load_model(FILER_IMAGE_MODEL)


class ImportFilesTestCase(TestCase):
    def setUp(self):
        # assets/readme.txt and assets/photos/pic.jpg
        self.tmp_dir = tempfile.mkdtemp()
        self.src = os.path.join(self.tmp_dir, 'assets')
        os.makedirs(os.path.join(self.src, 'photos'))
        with open(os.path.join(self.src, 'readme.txt'), 'w') as f:
            f.write('hello')
        create_image().save(os.path.join(self.src, 'photos', 'pic.jpg'))

    def tearDown(self):
        for file_obj in File.objects.all():
            file_obj.delete()
        shutil.rmtree(self.tmp_dir)

    def import_files(self, **options):
        call_command('import_files', path=self.src, verbosity=0, **options)

    def test_import_directory_structure(self):
        self.import_files()

        self.assertEqual(
            sorted(folder.pretty_logical_path for folder in Folder.objects.all()),
            ['/assets', '/assets/photos'],
        )
        readme = File.objects.get(original_filename='readme.txt')
        self.assertNotIsInstance(readme, Image)
        self.assertEqual(readme.folder.pretty_logical_path, '/assets')
        with readme.file.open('rb') as f:
            self.assertEqual(f.read(), b'hello')
        picture = Image.objects.get(original_filename='pic.jpg')
        self.assertEqual(picture.folder.pretty_logical_path, '/assets/photos')

    def test_import_into_base_folder(self):
        self.import_files(base_folder='images/2026')

        self.assertEqual(
            sorted(folder.pretty_logical_path for folder in Folder.objects.all()),
            ['/images', '/images/2026', '/images/2026/assets', '/images/2026/assets/photos'],
        )

    def test_import_twice_does_not_duplicate_files(self):
        self.import_files()
        self.import_files()

        self.assertEqual(Folder.objects.count(), 2)
        self.assertEqual(File.objects.count(), 2)


class GenerateThumbnailsTestCase(TestCase):
    def setUp(self):
        self.image = Image.objects.create(
            original_filename='pic.jpg',
            file=ContentFile(self._jpeg_bytes(), name='pic.jpg'),
        )

    def tearDown(self):
        self.image.delete()

    @staticmethod
    def _jpeg_bytes():
        buffer = BytesIO()
        create_image().save(buffer, format='JPEG')
        return buffer.getvalue()

    def test_generate_thumbnails(self):
        out = StringIO()
        call_command('generate_thumbnails', stdout=out)

        self.assertIn('Processing image 1 / 1', out.getvalue())
        self.assertTrue(self.image.thumbnails)
