#-*- coding: utf-8 -*-
import os
import zipfile
import tempfile
from django.forms.models import modelform_factory
from django.db.models import Q
from django.test import TestCase
from django.core.files import File as DjangoFile
from django.core.files.base import ContentFile

from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.models.filemodels import File
from filer.models.archivemodels import Archive
from filer.models.clipboardmodels import Clipboard
from filer.tests.helpers import (create_superuser, create_folder_structure,
                                 create_image, create_clipboard_item)
from filer import settings as filer_settings



class FilerApiTests(TestCase):

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for f in File.objects.all():
            f.delete()

    def create_filer_image(self):
        file_obj= DjangoFile(open(self.filename), name=self.image_name)
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
        file_obj = DjangoFile(open(self.filename), name=self.image_name)
        ImageUploadForm = modelform_factory(Image, fields=('original_filename', 'owner', 'file'))
        upoad_image_form = ImageUploadForm({'original_filename':self.image_name,
                                                'owner': self.superuser.pk},
                                                {'file':file_obj})
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

    def test_create_icons(self):
        image = self.create_filer_image()
        image.save()
        icons = image.icons
        file_basename = os.path.basename(image.file.path)
        self.assertEqual(len(icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        for size in filer_settings.FILER_ADMIN_ICON_SIZES:
            self.assertEqual(os.path.basename(icons[size]),
                             file_basename + u'__%sx%s_q85_crop_upscale.jpg' %(size,size))

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
        file_obj = DjangoFile(open(self.filename), name=self.image_name)

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

    def test_deleting_image_deletes_file_from_filesystem(self):
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

    def test_deleting_file_does_not_delete_file_from_filesystem_if_other_references_exist(self):
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


class ArchiveTest(TestCase):

    def setUp(self):
        self.entries = []
        self.zipname = 'test.zip'
        root = self.create_and_register_directory(None)
        subdir1 = self.create_and_register_directory(root)
        subdir2 = self.create_and_register_directory(root)
        subdir3 = self.create_and_register_directory(root)
        subdir11 = self.create_and_register_directory(subdir1)
        subdir12 = self.create_and_register_directory(subdir1)
        subdir21 = self.create_and_register_directory(subdir2)
        subdir31 = self.create_and_register_directory(subdir3)
        leaf1 = self.create_and_register_file(root, 'first leaf')
        leaf2 = self.create_and_register_file(subdir11, 'second leaf')
        leaf3 = self.create_and_register_file(subdir11, 'third leaf')
        leaf4 = self.create_and_register_file(subdir11, 'fourth leaf')
        leaf5 = self.create_and_register_file(subdir12, 'fifth leaf')
        leaf6 = self.create_and_register_file(subdir2, 'sixth leaf')
        leaf7 = self.create_and_register_file(subdir2, 'seventh leaf')
        leaf8 = self.create_and_register_file(subdir3, 'eight leaf')
        self.create_zipfile()
        filer_zipfile = Archive.objects.get()
        filer_zipfile.extract()

    def test_entries_count(self):
        files = File.objects.filter(~Q(original_filename=self.zipname))
        folders = Folder.objects.filter(~Q(name='tmp'))
        filer_entries = list(files) + list(folders)
        actual = len(filer_entries)
        expected = len(self.entries)
        self.assertEqual(actual, expected)

    def test_entries_path(self):
        files = File.objects.all()
        folders = Folder.objects.all()
        for entry in self.entries:
            basename = os.path.basename(entry)
            file_match = files.filter(original_filename=basename)
            folder_match = folders.filter(name=basename)
            filer_matches = file_match or folder_match
            self.assertNotEqual(0, len(filer_matches))
            filer_entry = filer_matches[0]
            fields = map(lambda x: x.name, filer_entry.logical_path)
            fields += [filer_entry.name or filer_entry.original_filename]
            filer_path = os.sep + os.sep.join(fields)
            self.assertEqual(filer_path, entry)

    def tearDown(self):
        os.remove('test.zip')
        for entry in reversed(self.entries):
            if os.path.isdir(entry):
                os.rmdir(entry)
            elif os.path.isfile(entry):
                os.remove(entry)

    def create_and_register_file(self, parent, data):
        fd, path = tempfile.mkstemp(dir=parent)
        os.write(fd, data)
        os.close(fd)
        self.entries.extend([path])
        return path

    def create_and_register_directory(self, parent):
        new_dir = tempfile.mkdtemp(dir=parent)
        self.entries.extend([new_dir])
        return new_dir

    def create_zipfile(self):
        zippy = zipfile.ZipFile(self.zipname, 'w')
        for entry in self.entries:
            zippy.write(entry)
        zippy.close()
        file_obj = DjangoFile(open(self.zipname), name=self.zipname)
        filer_zipfile = Archive.objects.create(
            original_filename=self.zipname,
            file=file_obj,
        )
