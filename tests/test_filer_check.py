import os
import shutil
import tempfile
from io import BytesIO, StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.utils.module_loading import import_string
from django.core.files.base import ContentFile

from filer import settings as filer_settings
from filer.models.filemodels import File
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from tests.helpers import create_image

Image = load_model(FILER_IMAGE_MODEL)


class FilerCheckTestCase(TestCase):
    svg_file_string = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "
    http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
    <svg version="1.1" baseProfile="full" width="50" height="50" xmlns="http://www.w3.org/2000/svg">
       <polygon id="triangle" points="0,0 0,50 50,0" fill="#009900"
    stroke="#004400"/>
       {}
    </svg>"""

    def setUp(self):
        # Clear all configured storages to ensure a clean state for each test.
        # This prevents interference from files left in any storage.
        for storage_alias, storage_configs in filer_settings.FILER_STORAGES.items():
            config = storage_configs.get('main')
            if not config:
                continue
            storage = import_string(config['ENGINE'])()
            upload_prefix = config.get('UPLOAD_TO_PREFIX', '')
            if storage.exists(upload_prefix):
                shutil.rmtree(storage.path(upload_prefix))

        # Create a sample file for testing in the public storage.
        original_filename = 'testimage.jpg'
        file_obj = SimpleUploadedFile(
            name=original_filename,
            content=create_image().tobytes(),
            content_type='image/jpeg'
        )
        self.filer_file = File.objects.create(
            file=file_obj,
            original_filename=original_filename
        )

    def tearDown(self):
        self.filer_file.delete()

    def test_delete_missing(self):
        out = StringIO()
        self.assertTrue(os.path.exists(self.filer_file.file.path))
        file_pk = self.filer_file.id
        call_command('filer_check', stdout=out, missing=True)
        self.assertEqual('', out.getvalue())

        # Remove the file to simulate a missing file.
        os.remove(self.filer_file.file.path)
        call_command('filer_check', stdout=out, missing=True)
        # When verbosity is low, a simple relative file path is output.
        self.assertEqual("None/testimage.jpg\n", out.getvalue())
        self.assertIsInstance(File.objects.get(id=file_pk), File)

        call_command('filer_check', delete_missing=True, interactive=False, verbosity=0)
        with self.assertRaises(File.DoesNotExist):
            File.objects.get(id=file_pk)

    def test_delete_orphans_public(self):
        # First check - should be empty initially
        out = StringIO()
        call_command('filer_check', stdout=out, orphans=True, verbosity=1)
        self.assertEqual('', out.getvalue())

        # Add an orphan file using the storage API directly
        public_settings = filer_settings.FILER_STORAGES['public']['main']
        storage = import_string(public_settings['ENGINE'])()

        # Configure storage location if specified in settings
        if public_settings.get('OPTIONS', {}).get('location'):
            storage.location = public_settings['OPTIONS']['location']

        # Get upload prefix and create file path
        prefix = public_settings.get('UPLOAD_TO_PREFIX', '')
        file_path = 'hello.txt'
        rel_path = os.path.join(prefix, file_path) if prefix else file_path

        # Save file through storage API
        storage.save(rel_path, ContentFile(b"I don't belong here!"))
        self.assertTrue(storage.exists(rel_path))

        # Check if orphan is detected
        out = StringIO()
        call_command('filer_check', stdout=out, orphans=True, verbosity=1)
        self.assertEqual("public/hello.txt\n", out.getvalue())

        # Delete orphans
        call_command('filer_check', delete_orphans=True, interactive=False, verbosity=0)
        self.assertFalse(storage.exists(rel_path))

    def test_delete_orphans_private(self):
        # Skip test if private storage is not configured.
        if 'private' not in filer_settings.FILER_STORAGES:
            self.skipTest("Private storage not configured in FILER_STORAGES.")

        out = StringIO()
        private_settings = filer_settings.FILER_STORAGES['private']['main']
        storage = import_string(private_settings['ENGINE'])()
        # Set storage location if defined in OPTIONS.
        if private_settings.get('OPTIONS', {}).get('location'):
            storage.location = private_settings['OPTIONS']['location']
        private_path = storage.path(private_settings.get('UPLOAD_TO_PREFIX', ''))
        os.makedirs(private_path, exist_ok=True)

        orphan_file = os.path.join(private_path, 'private_orphan.txt')
        with open(orphan_file, 'w') as fh:
            fh.write("I don't belong here!")
        # Run the command and check that it detects the private orphan file.
        call_command('filer_check', stdout=out, orphans=True)
        self.assertIn("private_orphan.txt", out.getvalue())
        self.assertTrue(os.path.exists(orphan_file))

        # Delete the orphan file.
        call_command('filer_check', delete_orphans=True, interactive=False, verbosity=0)
        self.assertFalse(os.path.exists(orphan_file))

    def test_delete_orphans_multiple_storages(self):
        """
        Test that the filer_check command correctly handles orphaned files in multiple storages
        without permanently modifying the settings. We use monkey-patching to assign temporary
        directories to the storage configurations.
        """
        out = StringIO()

        # --- Monkey-patch public storage location ---
        public_config = filer_settings.FILER_STORAGES['public']['main']
        temp_public_dir = tempfile.mkdtemp()
        if 'OPTIONS' in public_config:
            public_config['OPTIONS']['location'] = temp_public_dir
        else:
            public_config['OPTIONS'] = {'location': temp_public_dir}
        # Determine the upload prefix (if any) and ensure the corresponding directory exists.
        public_upload_prefix = public_config.get('UPLOAD_TO_PREFIX', '')
        if public_upload_prefix:
            public_full_dir = os.path.join(temp_public_dir, public_upload_prefix)
        else:
            public_full_dir = temp_public_dir
        os.makedirs(public_full_dir, exist_ok=True)

        # --- Monkey-patch private storage location ---
        private_config = filer_settings.FILER_STORAGES.get('private', {}).get('main')
        if private_config:
            temp_private_dir = tempfile.mkdtemp()
            if 'OPTIONS' in private_config:
                private_config['OPTIONS']['location'] = temp_private_dir
            else:
                private_config['OPTIONS'] = {'location': temp_private_dir}
            private_upload_prefix = private_config.get('UPLOAD_TO_PREFIX', '')
            if private_upload_prefix:
                private_full_dir = os.path.join(temp_private_dir, private_upload_prefix)
            else:
                private_full_dir = temp_private_dir
            os.makedirs(private_full_dir, exist_ok=True)
        else:
            self.skipTest("Private storage not configured in FILER_STORAGES.")

        # --- Initialize storages using the patched locations ---
        from django.core.files.storage import FileSystemStorage
        storage_public = FileSystemStorage(location=temp_public_dir)
        storage_private = FileSystemStorage(location=private_config['OPTIONS']['location'])

        # --- Save dummy orphan files in both storages ---
        # For public storage, include the upload prefix in the filename if needed.
        if public_upload_prefix:
            filename_public = os.path.join(public_upload_prefix, 'orphan_public.txt')
        else:
            filename_public = 'orphan_public.txt'
        if private_config.get('UPLOAD_TO_PREFIX', ''):
            filename_private = os.path.join(private_config['UPLOAD_TO_PREFIX'], 'orphan_private.txt')
        else:
            filename_private = 'orphan_private.txt'

        storage_public.save(filename_public, ContentFile(b"dummy content"))
        storage_private.save(filename_private, ContentFile(b"dummy content"))

        # --- Run the filer_check command ---
        call_command('filer_check', stdout=out, orphans=True)
        output = out.getvalue()

        # Verify that the output contains indicators for both storages.
        self.assertIn('public', output)
        self.assertIn('private', output)

        # --- Clean up ---
        storage_public.delete(filename_public)
        storage_private.delete(filename_private)
        shutil.rmtree(temp_public_dir)
        shutil.rmtree(private_config['OPTIONS']['location'])

    def test_image_dimensions_corrupted_file(self):
        original_filename = 'testimage.jpg'
        file_obj = SimpleUploadedFile(
            name=original_filename,
            content=create_image().tobytes(),  # Simulate a corrupted file.
            content_type='image/jpeg'
        )
        self.filer_image = Image.objects.create(
            file=file_obj,
            original_filename=original_filename
        )
        self.filer_image._width = 0
        self.filer_image.save()
        call_command('filer_check', image_dimensions=True)

    def test_image_dimensions_file_not_found(self):
        self.filer_image = Image.objects.create(
            file="123.jpg",
            original_filename="123.jpg"
        )
        call_command('filer_check', image_dimensions=True)
        self.filer_image.refresh_from_db()

    def test_image_dimensions(self):
        original_filename = 'testimage.jpg'
        with BytesIO() as jpg:
            create_image().save(jpg, format='JPEG')
            jpg.seek(0)
            file_obj = SimpleUploadedFile(
                name=original_filename,
                content=jpg.read(),
                content_type='image/jpeg'
            )
            self.filer_image = Image.objects.create(
                file=file_obj,
                original_filename=original_filename
            )
        self.filer_image._width = 0
        self.filer_image.save()

        call_command('filer_check', image_dimensions=True)
        self.filer_image.refresh_from_db()
        self.assertGreater(self.filer_image._width, 0)

    def test_image_dimensions_invalid_svg(self):
        original_filename = 'test.svg'
        svg_file = bytes("<asdva>" + self.svg_file_string, "utf-8")
        file_obj = SimpleUploadedFile(
            name=original_filename,
            content=svg_file,
            content_type='image/svg+xml'
        )
        self.filer_image = Image.objects.create(
            file=file_obj,
            original_filename=original_filename
        )
        self.filer_image._width = 0
        self.filer_image.save()
        call_command('filer_check', image_dimensions=True)

    def test_image_dimensions_svg(self):
        original_filename = 'test.svg'
        svg_file = bytes(self.svg_file_string, "utf-8")
        file_obj = SimpleUploadedFile(
            name=original_filename,
            content=svg_file,
            content_type='image/svg+xml'
        )
        self.filer_image = Image.objects.create(
            file=file_obj,
            original_filename=original_filename
        )
        self.filer_image._width = 0
        self.filer_image.save()

        call_command('filer_check', image_dimensions=True)
        self.filer_image.refresh_from_db()
        self.assertGreater(self.filer_image._width, 0)
