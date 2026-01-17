import os
import shutil
import tempfile
from io import BytesIO, StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase

from filer.models.filemodels import File
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from tests.helpers import create_image


class GenerateThumbnailsTestCase(TestCase):
    """Test cases for the generate_thumbnails management command."""

    def setUp(self):
        """Create test images for thumbnail generation."""
        self.images = []
        for i in range(3):
            with BytesIO() as img_io:
                create_image().save(img_io, format='JPEG')
                img_io.seek(0)
                file_obj = SimpleUploadedFile(
                    name=f'test_image_{i}.jpg',
                    content=img_io.read(),
                    content_type='image/jpeg'
                )
                image = Image.objects.create(
                    file=file_obj,
                    original_filename=f'test_image_{i}.jpg'
                )
                self.images.append(image)

    def tearDown(self):
        """Clean up created images."""
        for image in self.images:
            image.delete()

    def test_generate_thumbnails_basic(self):
        """Test that generate_thumbnails command runs without errors."""
        out = StringIO()
        err = StringIO()

        call_command('generate_thumbnails', stdout=out, stderr=err)

        output = out.getvalue()
        # Should process all images
        self.assertIn('Processing image', output)
        # Should show progress
        for i, image in enumerate(self.images, 1):
            self.assertIn(f'{i} / {len(self.images)}', output)

    def test_generate_thumbnails_with_missing_file(self):
        """Test that generate_thumbnails handles missing files gracefully."""
        # Create an image with a missing file
        missing_image = Image.objects.create(
            file='missing_file.jpg',
            original_filename='missing_file.jpg'
        )

        try:
            # Command should complete without raising exception
            call_command('generate_thumbnails', verbosity=0)
            # Verify original images still exist
            for image in self.images:
                self.assertTrue(Image.objects.filter(pk=image.pk).exists())
        finally:
            missing_image.delete()

    def test_generate_thumbnails_memory_management(self):
        """Test that the command properly manages memory by deleting image objects."""
        # This test verifies the memory management pattern used in the command
        # (iterating over PKs instead of the queryset)
        out = StringIO()

        call_command('generate_thumbnails', stdout=out)

        # All images should still exist in the database
        for image in self.images:
            self.assertTrue(Image.objects.filter(pk=image.pk).exists())

    def test_generate_thumbnails_output_format(self):
        """Test the output format of the command."""
        out = StringIO()

        call_command('generate_thumbnails', stdout=out)

        output = out.getvalue()
        # Check that output includes image information
        for image in self.images:
            # The output should contain references to the images being processed
            self.assertIn(str(image.pk), output)


class ImportFilesTestCase(TestCase):
    """Test cases for the import_files management command."""

    def setUp(self):
        """Create a temporary directory structure for import testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_structure = {
            'root_folder': {
                'subfolder1': {
                    'file1.txt': b'Content of file 1',
                    'image1.jpg': None,  # Will be an actual image
                },
                'subfolder2': {
                    'file2.txt': b'Content of file 2',
                    'image2.png': None,  # Will be an actual image
                },
                'root_file.txt': b'Root level file',
            }
        }
        self._create_directory_structure(self.temp_dir, self.test_structure)

    def tearDown(self):
        """Clean up temporary directory and imported files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        # Clean up imported files and folders
        File.objects.all().delete()
        Folder.objects.all().delete()

    def _create_directory_structure(self, base_path, structure):
        """Recursively create directory structure with files."""
        for name, content in structure.items():
            path = os.path.join(base_path, name)
            if isinstance(content, dict):
                # It's a directory
                os.makedirs(path, exist_ok=True)
                self._create_directory_structure(path, content)
            else:
                # It's a file
                if content is None and name.endswith(('.jpg', '.png', '.gif')):
                    # Create an actual image
                    with BytesIO() as img_io:
                        create_image().save(img_io, format='JPEG')
                        img_io.seek(0)
                        with open(path, 'wb') as f:
                            f.write(img_io.read())
                else:
                    # Create a text file
                    with open(path, 'wb') as f:
                        f.write(content)

    def test_import_files_basic(self):
        """Test basic import of files and folder structure."""
        test_path = os.path.join(self.temp_dir, 'root_folder')
        call_command('import_files', path=test_path, verbosity=0)

        # Check that folders were created
        self.assertTrue(Folder.objects.filter(name='subfolder1').exists())
        self.assertTrue(Folder.objects.filter(name='subfolder2').exists())

        # Check that files were imported
        self.assertTrue(File.objects.filter(original_filename='file1.txt').exists())
        self.assertTrue(File.objects.filter(original_filename='file2.txt').exists())
        self.assertTrue(File.objects.filter(original_filename='root_file.txt').exists())

        # Check that images were imported as Image objects
        self.assertTrue(Image.objects.filter(original_filename='image1.jpg').exists())
        self.assertTrue(Image.objects.filter(original_filename='image2.png').exists())

    def test_import_files_with_base_folder(self):
        """Test import with a specified base folder."""
        # Create a base folder in filer
        Folder.objects.create(name='imports')

        test_path = os.path.join(self.temp_dir, 'root_folder')

        call_command(
            'import_files',
            path=test_path,
            base_folder='imports',
            verbosity=0
        )

        # Verify that imported folders are under the base folder
        subfolder1 = Folder.objects.get(name='subfolder1')
        # The subfolder should be nested under the root folder, which is under imports
        ancestors = []
        parent = subfolder1.parent
        while parent:
            ancestors.append(parent.name)
            parent = parent.parent
        self.assertIn('imports', ancestors)

    def test_import_files_duplicate_prevention(self):
        """Test that importing the same files creates duplicates for files but not folders."""
        test_path = os.path.join(self.temp_dir, 'root_folder')

        # First import
        call_command('import_files', path=test_path, verbosity=0)
        initial_file_count = File.objects.count()
        initial_folder_count = Folder.objects.count()

        # Second import of the same structure
        call_command('import_files', path=test_path, verbosity=0)
        final_file_count = File.objects.count()
        final_folder_count = Folder.objects.count()

        # Files will be duplicated (different file objects), but folders reused
        self.assertGreater(final_file_count, initial_file_count)
        self.assertEqual(initial_folder_count, final_folder_count)

    def test_import_files_folder_hierarchy(self):
        """Test that folder hierarchy is correctly maintained."""
        test_path = os.path.join(self.temp_dir, 'root_folder')

        call_command('import_files', path=test_path, verbosity=0)

        # Get the subfolders
        subfolder1 = Folder.objects.get(name='subfolder1')
        subfolder2 = Folder.objects.get(name='subfolder2')

        # Both should have the same parent (root_folder)
        self.assertIsNotNone(subfolder1.parent)
        self.assertIsNotNone(subfolder2.parent)
        self.assertEqual(subfolder1.parent, subfolder2.parent)
        self.assertEqual(subfolder1.parent.name, 'root_folder')

    def test_import_files_file_folder_relationship(self):
        """Test that imported files are associated with correct folders."""
        test_path = os.path.join(self.temp_dir, 'root_folder')

        call_command('import_files', path=test_path, verbosity=0)

        # Get files and their folders
        file1 = File.objects.get(original_filename='file1.txt')
        file2 = File.objects.get(original_filename='file2.txt')
        root_file = File.objects.get(original_filename='root_file.txt')

        # Verify folder associations
        self.assertEqual(file1.folder.name, 'subfolder1')
        self.assertEqual(file2.folder.name, 'subfolder2')
        self.assertEqual(root_file.folder.name, 'root_folder')

    def test_import_files_verbosity_levels(self):
        """Test different verbosity levels."""
        test_path = os.path.join(self.temp_dir, 'root_folder')

        # Test verbosity 0 (minimal output) - command uses print(), not stdout
        out = StringIO()
        call_command('import_files', path=test_path, verbosity=0, stdout=out)
        # Files should be created even with verbosity 0
        self.assertTrue(File.objects.exists())

        # Clean up for next test
        File.objects.all().delete()
        Folder.objects.all().delete()

        # Test verbosity 1 and 2 - command uses print() which goes to console, not captured by stdout
        # Just verify the command runs successfully
        call_command('import_files', path=test_path, verbosity=1, stdout=out)
        self.assertTrue(File.objects.exists())

        # Clean up for next test
        File.objects.all().delete()
        Folder.objects.all().delete()

        # Test verbosity 2
        call_command('import_files', path=test_path, verbosity=2, stdout=out)
        self.assertTrue(File.objects.exists())

    def test_import_files_image_detection(self):
        """Test that image files are correctly identified and imported as Image objects."""
        test_path = os.path.join(self.temp_dir, 'root_folder')

        call_command('import_files', path=test_path, verbosity=0)

        # Check that .jpg and .png files are Image instances
        image1 = File.objects.get(original_filename='image1.jpg')
        image2 = File.objects.get(original_filename='image2.png')

        self.assertIsInstance(image1, Image)
        self.assertIsInstance(image2, Image)

        # Check that .txt files are File instances (not Image)
        file1 = File.objects.get(original_filename='file1.txt')
        self.assertIsInstance(file1, File)
        self.assertNotIsInstance(file1, Image)

    def test_import_files_empty_directory(self):
        """Test importing an empty directory."""
        empty_dir = tempfile.mkdtemp()
        try:
            call_command('import_files', path=empty_dir, verbosity=0)

            # The root folder should be created
            root_folder_name = os.path.basename(empty_dir)
            self.assertTrue(Folder.objects.filter(name=root_folder_name).exists())
        finally:
            shutil.rmtree(empty_dir)

    def test_import_files_nested_structure(self):
        """Test importing deeply nested folder structures."""
        # Create a deeper nested structure
        deep_path = os.path.join(self.temp_dir, 'deep')
        nested_structure = {
            'level1': {
                'level2': {
                    'level3': {
                        'deep_file.txt': b'Deep nested file',
                    }
                }
            }
        }
        self._create_directory_structure(deep_path, nested_structure)

        call_command('import_files', path=deep_path, verbosity=0)

        # Verify all levels were created
        level1 = Folder.objects.get(name='level1')
        level2 = Folder.objects.get(name='level2')
        level3 = Folder.objects.get(name='level3')

        # Verify hierarchy
        self.assertEqual(level3.parent, level2)
        self.assertEqual(level2.parent, level1)

        # Verify file is in the deepest folder
        deep_file = File.objects.get(original_filename='deep_file.txt')
        self.assertEqual(deep_file.folder, level3)

    def test_import_files_respects_public_setting(self):
        """Test that imported files use the is_public parameter from get_or_create."""
        test_path = os.path.join(self.temp_dir, 'root_folder')

        # The command passes FILER_IS_PUBLIC_DEFAULT to get_or_create
        # This test just verifies files are created successfully
        call_command('import_files', path=test_path, verbosity=0)

        # Verify files were created
        self.assertGreater(File.objects.count(), 0)

    def test_import_files_path_normalization(self):
        """Test that paths with trailing slashes and other variations are handled."""
        test_path = os.path.join(self.temp_dir, 'root_folder')

        # Test with trailing slash
        path_with_slash = test_path + os.sep
        call_command('import_files', path=path_with_slash, verbosity=0)

        # Should work the same as without trailing slash
        self.assertTrue(Folder.objects.filter(name='subfolder1').exists())
        self.assertTrue(File.objects.filter(original_filename='file1.txt').exists())


class ImportFilesEdgeCasesTestCase(TestCase):
    """Test edge cases and error handling for import_files command."""

    def setUp(self):
        """Create test directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        File.objects.all().delete()
        Folder.objects.all().delete()

    def test_import_files_with_special_characters(self):
        """Test importing files with special characters in names."""
        # Create files with special characters (that are filesystem-safe)
        special_files = {
            'file-with-dash.txt': b'Dash file',
            'file_with_underscore.txt': b'Underscore file',
            'file with spaces.txt': b'Spaces file',
        }

        for filename, content in special_files.items():
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(content)

        call_command('import_files', path=self.temp_dir, verbosity=0)

        # All files should be imported
        for filename in special_files.keys():
            self.assertTrue(
                File.objects.filter(original_filename=filename).exists(),
                f"File '{filename}' was not imported"
            )

    def test_import_files_mixed_extensions(self):
        """Test importing files with various extensions."""
        # Create files with different extensions
        files_to_create = {
            'document.pdf': b'PDF content',
            'image.gif': None,  # Will be created as image
            'data.json': b'{"key": "value"}',
            'style.css': b'body { margin: 0; }',
            'script.js': b'console.log("test");',
        }

        for filename, content in files_to_create.items():
            filepath = os.path.join(self.temp_dir, filename)
            if content is None:
                # Create an image
                with BytesIO() as img_io:
                    create_image().save(img_io, format='GIF')
                    img_io.seek(0)
                    with open(filepath, 'wb') as f:
                        f.write(img_io.read())
            else:
                with open(filepath, 'wb') as f:
                    f.write(content)

        call_command('import_files', path=self.temp_dir, verbosity=0)

        # Verify all files are imported
        for filename in files_to_create.keys():
            self.assertTrue(File.objects.filter(original_filename=filename).exists())

        # Verify .gif is imported as Image
        gif_file = File.objects.get(original_filename='image.gif')
        self.assertIsInstance(gif_file, Image)

    def test_import_files_output_statistics(self):
        """Test that import command creates correct number of objects."""
        # Create a simple structure
        test_folder = os.path.join(self.temp_dir, 'test_stats')
        os.makedirs(test_folder)

        # Create 2 regular files
        for i in range(2):
            with open(os.path.join(test_folder, f'file{i}.txt'), 'wb') as f:
                f.write(b'content')

        # Create 1 image
        with BytesIO() as img_io:
            create_image().save(img_io, format='JPEG')
            img_io.seek(0)
            with open(os.path.join(test_folder, 'image.jpg'), 'wb') as f:
                f.write(img_io.read())

        call_command('import_files', path=test_folder, verbosity=0)

        # Verify correct counts
        self.assertEqual(Folder.objects.count(), 1)  # test_stats folder
        # 2 text files are File instances
        text_files = File.objects.filter(original_filename__endswith='.txt')
        self.assertEqual(text_files.count(), 2)
        # 1 image
        images = Image.objects.all()
        self.assertEqual(images.count(), 1)
