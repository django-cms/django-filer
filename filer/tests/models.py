# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os

from django.conf import settings
from django.core.files import File as DjangoFile
from django.forms.models import modelform_factory
from django.test import TestCase

from .. import settings as filer_settings
from ..models.clipboardmodels import Clipboard
from ..models.filemodels import File
from ..models.foldermodels import Folder
from ..models.mixins import IconsMixin
from ..settings import FILER_IMAGE_MODEL
from ..test_utils import ET_2
from ..utils.loader import load_model
from .helpers import (
    create_clipboard_item,
    create_folder_structure,
    create_image,
    create_superuser,
)

Image = load_model(FILER_IMAGE_MODEL)

try:
    from unittest import skipIf, skipUnless
except ImportError:
    # Django<1.9
    from django.utils.unittest import skipIf, skipUnless



class FilerApiTests(TestCase):

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, 'JPEG')

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for f in File.objects.all():
            f.delete()

    def create_filer_image(self):
        file_obj = DjangoFile(open(self.filename, 'rb'), name=self.image_name)
        image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=file_obj)
        return image

    def test_create_folder_structure(self):
        create_folder_structure(depth=3, sibling=2, parent=None)
        self.assertEqual(Folder.objects.count(), 26)

    def test_create_and_delete_image(self):
        self.assertEqual(Image.objects.count(), 0)
        image = self.create_filer_image()
        image.save()
        self.assertEqual(Image.objects.count(), 1)
        image = Image.objects.all()[0]
        image.delete()
        self.assertEqual(Image.objects.count(), 0)

    def test_upload_image_form(self):
        self.assertEqual(Image.objects.count(), 0)
        file_obj = DjangoFile(open(self.filename, 'rb'), name=self.image_name)
        ImageUploadForm = modelform_factory(Image, fields=('original_filename', 'owner', 'file'))
        upoad_image_form = ImageUploadForm({'original_filename': self.image_name,
                                                'owner': self.superuser.pk},
                                                {'file': file_obj})
        if upoad_image_form.is_valid():
            image = upoad_image_form.save()
        self.assertEqual(Image.objects.count(), 1)

    def test_create_clipboard_item(self):
        image = self.create_filer_image()
        image.save()
        # Get the clipboard of the current user
        clipboard_item = create_clipboard_item(user=self.superuser,
            file_obj=image)
        clipboard_item.save()
        self.assertEqual(Clipboard.objects.count(), 1)

    @skipIf(ET_2, 'Skipping for easy_thumbnails version >= 2.0')
    def test_create_icons(self):
        image = self.create_filer_image()
        image.save()
        icons = image.icons
        file_basename = os.path.basename(image.file.path)
        self.assertEqual(len(icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        for size in filer_settings.FILER_ADMIN_ICON_SIZES:
            self.assertEqual(os.path.basename(icons[size]),
                             file_basename + '__%sx%s_q85_crop_upscale.jpg' % (size, size))

    @skipUnless(ET_2, 'Skipping for easy_thumbnails version < 2.0')
    def test_create_icons(self):
        image = self.create_filer_image()
        image.save()
        icons = image.icons
        file_basename = os.path.basename(image.file.path)
        self.assertEqual(len(icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        for size in filer_settings.FILER_ADMIN_ICON_SIZES:
            self.assertEqual(os.path.basename(icons[size]),
                             file_basename + '__%sx%s_q85_crop_subsampling-2_upscale.jpg' % (size, size))

    def test_access_icons_property(self):
        """Test IconsMixin that calls static on a non-existent file"""

        class CustomObj(IconsMixin, object):
            _icon = 'custom'

        custom_obj = CustomObj()
        try:
            icons = custom_obj.icons
        except Exception as e:
            self.fail("'.icons' access raised Exception {0} unexpectedly!".format(e))
        self.assertEqual(len(icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))

    def test_file_upload_public_destination(self):
        """
        Test where an image `is_public` == True is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))

    def test_file_upload_private_destination(self):
        """
        Test where an image `is_public` == False is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))

    def test_file_move_location(self):
        """
        Test the method that move a file between filer_public, filer_private
        and vice et versa
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))

    def test_file_change_upload_to_destination(self):
        """
        Test that the file is actualy move from the private to the public
        directory when the is_public is checked on an existing private file.
        """
        file_obj = DjangoFile(open(self.filename, 'rb'), name=self.image_name)

        image = Image.objects.create(owner=self.superuser,
                                     is_public=False,
                                     original_filename=self.image_name,
                                     file=file_obj)
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))

    def test_deleting_files(self):
        # Note: this first test case fails deep inside
        # easy-thumbnails thumbnail generation with a segmentation fault
        # (which probably indicates a fail inside C extension or reaching
        # CPython stack limits) under certain conditions:
        #  - if the previous test case had the create_filer_image() call
        #  - under python 3.x
        #  - once out of 3-4 runs
        # It happens on completely different systems (locally and on Travis).
        # Current tearDown() does not help, nor does cleaning up temp directory
        # nor django cache.
        # So the workaround for now is to run them in a defined order like one
        # real test case. We do not care for setUp() or tearDown() between the
        # two since there are enough asserts in the code.
        self._test_deleting_image_deletes_file_from_filesystem()
        self._test_deleting_file_does_not_delete_file_from_filesystem_if_other_references_exist()

    def _test_deleting_image_deletes_file_from_filesystem(self):
        file_1 = self.create_filer_image()
        self.assertTrue(file_1.file.storage.exists(file_1.file.name))

        # create some thumbnails
        thumbnail_urls = file_1.thumbnails

        # check if the thumnails exist
        thumbnails = [x for x in file_1.file.get_thumbnails()]
        for tn in thumbnails:
            self.assertTrue(tn.storage.exists(tn.name))
        storage, name = file_1.file.storage, file_1.file.name

        # delete the file
        file_1.delete()

        # file should be gone
        self.assertFalse(storage.exists(name))
        # thumbnails should be gone
        for tn in thumbnails:
            self.assertFalse(tn.storage.exists(tn.name))

    def _test_deleting_file_does_not_delete_file_from_filesystem_if_other_references_exist(self):
        file_1 = self.create_filer_image()
        # create another file that references the same physical file
        file_2 = File.objects.get(pk=file_1.pk)
        file_2.pk = None
        file_2.id = None
        file_2.save()
        self.assertTrue(file_1.file.storage.exists(file_1.file.name))
        self.assertTrue(file_2.file.storage.exists(file_2.file.name))
        self.assertEqual(file_1.file.name, file_2.file.name)
        self.assertEqual(file_1.file.storage, file_2.file.storage)

        storage, name = file_1.file.storage, file_1.file.name

        # delete one file
        file_1.delete()

        # file should still be here
        self.assertTrue(storage.exists(name))

    def test_folder_quoted_logical_path(self):
        root_folder = Folder.objects.create(name="Foo's Bar", parent=None)
        child = Folder.objects.create(name='Bar"s Foo', parent=root_folder)
        self.assertEqual(child.quoted_logical_path, '/Foo%27s%20Bar/Bar%22s%20Foo')

    def test_folder_quoted_logical_path_with_unicode(self):
        root_folder = Folder.objects.create(name="Foo's Bar", parent=None)
        child = Folder.objects.create(name='Bar"s 日本 Foo', parent=root_folder)
        self.assertEqual(child.quoted_logical_path,
                         '/Foo%27s%20Bar/Bar%22s%20%E6%97%A5%E6%9C%AC%20Foo')

    def test_custom_model(self):
        """
        Check that the correct model is loaded and save / reload data
        """
        def swapped_image_test(image):
            self.assertTrue(hasattr(image, 'extra_description'))
            self.assertFalse(hasattr(image, 'author'))
            image.extra_description = 'Extra'
            image.save()

            reloaded = Image.objects.get(pk=image.pk)
            self.assertEqual(reloaded.extra_description, image.extra_description)

        def unswapped_image_test(image):
            self.assertFalse(hasattr(image, 'extra_description'))
            self.assertTrue(hasattr(image, 'author'))
            image.author = 'Me'
            image.save()

            reloaded = Image.objects.get(pk=image.pk)
            self.assertEqual(reloaded.author, image.author)

        test_image = self.create_filer_image()
        try:
            from filer.models import Image as DefaultImage
            if DefaultImage._meta.swapped:
                swapped_image_test(test_image)
            else:
                unswapped_image_test(test_image)
        except ImportError:
            swapped_image_test(test_image)

    def test_canonical_url(self):
        """
        Check that a public file's canonical url redirects to the file's current version
        """
        image = self.create_filer_image()
        image.save()
        # Private file
        image.is_public = False
        image.save()
        canonical = image.canonical_url
        self.assertEqual(self.client.get(canonical).status_code, 404)
        # First public version
        image.is_public = True
        image.save()
        canonical = image.canonical_url
        file_url_1 = image.file.url
        self.assertRedirects(self.client.get(canonical), file_url_1)
        # Second public version
        img_2 = create_image()
        image_name_2 = 'test_file_2.jpg'
        filename_2 = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, image_name_2)
        img_2.save(filename_2, 'JPEG')
        file_2 = DjangoFile(open(filename_2, 'rb'), name=image_name_2)
        image.file = file_2
        image.save()
        file_url_2 = image.file.url
        self.assertNotEqual(file_url_1, file_url_2)
        self.assertRedirects(self.client.get(canonical), file_url_2)
        # No file
        image.file = None
        image.save()
        self.assertEqual(self.client.get(canonical).status_code, 404)
        # Teardown
        image.file = file_2
        image.save()
        os.remove(filename_2)

    def test_canonical_url_settings(self):
        image = self.create_filer_image()
        image.save()
        canonical = image.canonical_url
        self.assertTrue(canonical.startswith('/filer/test-path/'))
