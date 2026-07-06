"""Tests for filer.utils.loader."""

from django.test import TestCase

from filer.utils.loader import load_object, load_model, storage_factory


class LoadObjectTests(TestCase):
    """Tests for load_object."""

    def test_load_valid_object(self):
        result = load_object('filer.utils.loader.load_object')
        self.assertTrue(callable(result))

    def test_load_non_string_returns_self(self):
        obj = object()
        result = load_object(obj)
        self.assertIs(result, obj)

    def test_load_no_dot_raises_type_error(self):
        with self.assertRaises(TypeError):
            load_object('nodot')

    def test_load_invalid_module_raises_import_error(self):
        with self.assertRaises(ImportError):
            load_object('nonexistent.module.Class')

    def test_load_invalid_attribute_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            load_object('filer.utils.loader.NonExistentAttribute')


class LoadModelTests(TestCase):
    """Tests for load_model."""

    def test_load_model(self):
        result = load_model('filer.File')
        from filer.models.filemodels import File
        self.assertIs(result, File)

    def test_load_image_model(self):
        result = load_model('filer.Image')
        from filer.models.imagemodels import Image
        self.assertIs(result, Image)


class StorageFactoryTests(TestCase):
    """Tests for storage_factory."""

    def test_storage_factory(self):
        from django.core.files.storage import FileSystemStorage
        storage = storage_factory(FileSystemStorage, '/tmp/test', '/media/test/')
        self.assertIsInstance(storage, FileSystemStorage)
        self.assertEqual(storage.location, '/tmp/test')
        self.assertEqual(storage.base_url, '/media/test/')
