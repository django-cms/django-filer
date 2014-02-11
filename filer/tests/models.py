#-*- coding: utf-8 -*-
import os
import tempfile
import urlparse
import zipfile
import time

from django.forms.models import modelform_factory
from django.db.models import Q
from django.test import TestCase
from django.core.files import File as DjangoFile
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.contrib.admin import helpers
from django.core import files as dj_files
from django.contrib.sites.models import Site

from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.models.filemodels import File
from filer.models.archivemodels import Archive
from filer.models.clipboardmodels import Clipboard
from filer.tests.helpers import (
    get_dir_listing_url, create_superuser, create_folder_structure,
    create_image, create_clipboard_item, SettingsOverride,
    filer_obj_as_checkox)
from django.test.utils import override_settings
from filer import settings as filer_settings
from filer.utils.generate_filename import by_path



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
        for f in File.all_objects.all():
            f.delete(to_trash=False)

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
        image.delete(to_trash=False)
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

    def test_folder_rename_updates_file_urls(self):
        with SettingsOverride(filer_settings,
                              FILER_PUBLICMEDIA_UPLOAD_TO=by_path,
                              FOLDER_AFFECTS_URL=True):
            folder = Folder(name='foo')
            folder.save()
            file_obj = DjangoFile(open(self.filename))
            afile = File(name='testfile', folder=folder, file=file_obj)
            afile.save()
            self.assertIn('foo/testfile', afile.url)
            folder.name = 'bar'
            folder.save()
            # refetch from db
            afile = File.objects.get(pk=afile.pk)
            self.assertIn('bar/testfile', afile.url)

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

    def test_deleting_folder_deletes_all_files_from_filesystem(self):
        folder = Folder.objects.create(name='to_delete')
        file_1 = self.create_filer_image()
        file_1.folder = folder
        file_1.save()
        storage, name = file_1.file.storage, file_1.file.name
        self.assertTrue(storage.exists(name))
        folder.delete(to_trash=False)
        self.assertFalse(storage.exists(name))

    def test_bulk_deleting_folder_deletes_all_files_from_filesystem(self):
        folder = Folder.objects.create(name='to_delete2')
        file_1 = self.create_filer_image()
        file_1.folder = folder
        file_1.save()
        storage, name = file_1.file.storage, file_1.file.name

        response = self.client.post(get_dir_listing_url(None), {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: filer_obj_as_checkox(folder),
        })

        self.assertTrue(storage.exists('_trash/%s/to_delete2/%s' % (
            file_1.pk, self.image_name)))
        self.assertFalse(storage.exists(name))
        folder.delete(to_trash=False)
        self.assertFalse(storage.exists(name))
        self.assertFalse(storage.exists('_trash/%s/to_delete2/%s' % (
            file_1.pk, self.image_name)))

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
        file_1.delete(to_trash=False)

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
        file_1.delete(to_trash=False)

        # file should still be here
        self.assertTrue(storage.exists(name))

    def test_credit_text_length_max_size(self):
        file_1 = self.create_filer_image()
        file_1.full_clean()
        file_1.default_credit = '*' * 31
        with self.assertRaises(ValidationError):
            file_1.full_clean()

    def test_slash_not_allowed_in_name(self):
        file_1 = self.create_filer_image()
        file_1.full_clean()
        file_1.name = "something/with/slash"
        with self.assertRaises(ValidationError):
            file_1.full_clean()

        folder = Folder.objects.create(
            name="cleaned", site_id=1)
        folder.full_clean()
        folder.name = "something/with/slash"
        with self.assertRaises(ValidationError):
            folder.full_clean()

    @override_settings(USE_TZ=True)
    def test_cdn_urls(self):
        cdn_domain = 'cdn.foobar.com'
        with SettingsOverride(filer_settings,
                              CDN_DOMAIN=cdn_domain,
                              USE_TZ=True,
                              CDN_INVALIDATION_TIME=1):
            image = self.create_filer_image()
            _, netloc, _, _, _, _ = urlparse.urlparse(image.url)
            self.assertEqual(netloc, '')
            time.sleep(1)
            _, netloc, _, _, _, _ = urlparse.urlparse(image.url)
            self.assertEqual(netloc, cdn_domain)
            for url in image.thumbnails.values():
                _, netloc, _, _, _, _ = urlparse.urlparse(url)
                self.assertEqual(netloc, cdn_domain)

    @override_settings(USE_TZ=False)
    def test_cdn_urls_no_timezone_support(self):
        cdn_domain = 'cdn.foobar.com'
        with SettingsOverride(filer_settings,
                              CDN_DOMAIN=cdn_domain,
                              USE_TZ=False,
                              CDN_INVALIDATION_TIME=1):
            image = self.create_filer_image()
            _, netloc, _, _, _, _ = urlparse.urlparse(image.url)
            self.assertEqual(netloc, '')
            time.sleep(1)
            _, netloc, _, _, _, _ = urlparse.urlparse(image.url)
            self.assertEqual(netloc, cdn_domain)
            for url in image.thumbnails.values():
                _, netloc, _, _, _, _ = urlparse.urlparse(url)
                self.assertEqual(netloc, cdn_domain)


class ArchiveTest(TestCase):

    def setUp(self):
        self.entries = []
        self.zipname = 'test.zip'
        self.root = root = self.create_and_register_directory(None)
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

    def test_collision_when_extracting(self):
        foo = Folder.objects.create(name="foo")
        # move zip into a folder
        archive = Archive.objects.get()
        archive.folder = foo
        archive.save()
        # no collisions should be detected
        self.assertEqual(archive.collisions(), [])
        # extract zip in the new folder
        Archive.objects.get().extract()
        # collisions should be detected
        self.assertNotEqual(Archive.objects.get().collisions(), [])
        # delete foo content and re-try
        for a_file in File.objects.exclude(id=archive.id).filter(folder=foo):
            a.delete()
        for subfolder in Folder.objects.filter(parent=foo):
            subfolder.delete()
        self.assertEqual(Archive.objects.get().collisions(), [])

    def test_entries_count(self):
        files = File.objects.filter(~Q(original_filename=self.zipname))
        tmp_basedir, _ = os.path.split(self.root)
        tmp_basedir_comp = tmp_basedir.strip(os.path.sep).split(os.path.sep)
        folders = [ff for ff in Folder.objects.exclude(name__in=tmp_basedir_comp)
                   if ff.pretty_logical_path.startswith(tmp_basedir)]
        filer_entries = list(files) + folders
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
        for f in File.all_objects.all():
            f.delete(to_trash=False)
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

    def test_folder_quoted_logical_path(self):
        root_folder = Folder.objects.create(name=u"Foo's Bar", parent=None)
        child = Folder.objects.create(name=u'Bar"s Foo', parent=root_folder)
        self.assertEqual(child.quoted_logical_path, u'/Foo%27s%20Bar/Bar%22s%20Foo')

    def test_folder_quoted_logical_path_with_unicode(self):
        root_folder = Folder.objects.create(name=u"Foo's Bar", parent=None)
        child = Folder.objects.create(name=u'Bar"s 日本 Foo', parent=root_folder)
        self.assertEqual(child.quoted_logical_path,
                         u'/Foo%27s%20Bar/Bar%22s%20%E6%97%A5%E6%9C%AC%20Foo')


class TrashableModelTestCase(TestCase):

    def tearDown(self):
        for f in File.all_objects.all():
            f.delete(to_trash=False)

    def test_files_deletion_is_soft_by_default(self):
        file_foo = File.objects.create(
            original_filename='file.txt',
            file=dj_files.base.ContentFile('some data'))
        file_foo.delete()
        self.assertTrue(File.trash.filter(pk=file_foo.pk).exists())
        self.assertFalse(File.objects.filter(pk=file_foo.pk).exists())
        self.assertEqual(File.trash.get(pk=file_foo.pk).file.name,
                         '_trash/%s/file.txt' % file_foo.pk)

    def create_filer_image(self, image_name):
        image = create_image()
        image_path = os.path.join(os.path.dirname(__file__), image_name)
        image.save(image_path, 'JPEG')
        file_obj = DjangoFile(open(image_path), name=image_name)
        image = Image.objects.create(original_filename=image_name,
                                     file=file_obj)
        os.remove(image_path)
        return image

    def test_trashed_files_dont_update_paths_if_tree_changes(self):
        img = self.create_filer_image('foo_image.jpg')
        folder = Folder.objects.create(name='foo')
        img.folder = folder
        img.save()
        img.delete()
        img = Image.trash.get(original_filename='foo_image.jpg')
        self.assertEqual(img.file.name, '_trash/%s/foo/foo_image.jpg' % img.pk)
        # rename folder
        folder.name = 'bar'
        # change metadata
        folder.restricted = True
        # add a parent with a site set
        folder.parent = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)
        folder.save()
        # trashed items should preserve metdata but should not change paths
        img = Image.trash.get(original_filename='foo_image.jpg')
        self.assertEqual(img.file.name, '_trash/%s/foo/foo_image.jpg'% img.pk)
        self.assertTrue(img.restricted)
        self.assertTrue(img.is_core())

    def test_file_soft_del_doesnt_remove_file_from_storage_if_other_refs(self):
        img1 = self.create_filer_image('foo_image.jpg')
        img2 = Image.objects.create(original_filename='foo_image.jpg')
        Image.objects.filter(id=img2.id).update(file=img1.file.name)
        img2 = Image.objects.get(id=img2.id)
        self.assertEqual(img1.file.name, img2.file.name)
        self.assertTrue(img1.file.storage.exists(img1.file.name))
        self.assertTrue(img2.file.storage.exists(img2.file.name))
        img2.delete()
        img1 = Image.objects.get(original_filename='foo_image.jpg')
        self.assertTrue(img1.file.storage.exists(img1.file.name))
        img2 = Image.trash.get(original_filename='foo_image.jpg')
        self.assertEqual(img2.file.name, '_trash/%s/foo_image.jpg'% img2.pk)

    def test_file_soft_del_works_if_file_missing_from_storage(self):
        img = self.create_filer_image('foo_image.jpg')
        img.file.storage.delete(img.file.name)
        img = Image.objects.get(original_filename='foo_image.jpg')
        self.assertFalse(img.file.storage.exists(img.file.name))
        img.delete()
        img = Image.trash.get(original_filename='foo_image.jpg')
        self.assertFalse(img.file.storage.exists(img.file.name))
        self.assertEqual(img.file.name, '_trash/%s/foo_image.jpg'% img.pk)

    def test_thumbnails_removed_when_source_is_soft_deleted(self):
        img = self.create_filer_image('foo_image.jpg')
        self.assertEqual(sum(1 for i in img.file.get_thumbnails()), 0)
        # generate some thumbnails
        generated_thumbnails = img.icons
        img.file.get_thumbnail({'size': (60, 80)})
        thumb_no = len(filer_settings.FILER_ADMIN_ICON_SIZES) + 1
        self.assertEqual(sum(1 for i in img.file.get_thumbnails()), thumb_no)
        img.delete()
        # soft deletes files shoudn't be able to generate thumbnails
        self.assertEqual(sum(1 for i in img.file.get_thumbnails()), 0)
        generated_thumbnails = img.icons
        self.assertEqual(img.file.get_thumbnail({'size': (60, 80)}), None)
        self.assertEqual(sum(1 for i in img.file.get_thumbnails()), 0)
        self.assertEqual(img.url, '')
        img.deleted_at = None
        # thumbnail generation should work after restoring
        generated_thumbnails = img.icons
        img.file.get_thumbnail({'size': (60, 80)})
        thumb_no = len(filer_settings.FILER_ADMIN_ICON_SIZES) + 1
        self.assertEqual(sum(1 for i in img.file.get_thumbnails()), thumb_no)

    def test_folders_deletion_is_soft_by_default(self):
        foo = Folder.objects.create(name='foo')
        file_foo = self.create_filer_image('image.jpg')
        file_foo.folder = foo
        file_foo.save()
        file_foo_pk = file_foo.pk
        foo_pk = foo.pk
        foo.delete()
        self.assertTrue(File.trash.filter(pk=file_foo_pk).exists())
        self.assertTrue(Folder.trash.filter(pk=foo_pk).exists())
        self.assertFalse(File.objects.filter(pk=file_foo_pk).exists())
        self.assertFalse(Folder.objects.filter(pk=foo_pk).exists())
        self.assertEqual(File.trash.get(pk=file_foo_pk).file.name,
                         '_trash/%s/foo/image.jpg' % file_foo_pk)
