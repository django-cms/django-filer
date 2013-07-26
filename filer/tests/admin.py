#-*- coding: utf-8 -*-
import os
from django.test import TestCase
from django.core.urlresolvers import reverse
import django.core.files
from django.contrib.admin import helpers
from django.contrib.auth.models import User
from django.conf import settings

from filer.models.filemodels import File
from filer.models.foldermodels import Folder, FolderPermission
from filer.models.imagemodels import Image
from filer.models.clipboardmodels import Clipboard
from filer.models.virtualitems import FolderRoot
from filer.models import tools
from filer.tests.helpers import (create_superuser, create_folder_structure,
                                 create_image, SettingsOverride)
from filer import settings as filer_settings


class FilerFolderAdminUrlsTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_filer_app_index_get(self):
        response = self.client.get(reverse('admin:app_list', args=('filer',)))
        self.assertEqual(response.status_code, 200)

    def test_filer_make_root_folder_get(self):
        response = self.client.get(reverse('admin:filer-directory_listing-make_root_folder')+"?_popup=1")
        self.assertEqual(response.status_code, 200)

    def test_filer_make_root_folder_post(self):
        FOLDER_NAME = "root folder 1"
        self.assertEqual(Folder.objects.count(), 0)
        response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'),
                                    {
                                        "name":FOLDER_NAME,
                                    })
        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, FOLDER_NAME)
        #TODO: not sure why the status code is 200
        self.assertEqual(response.status_code, 200)

    def test_filer_remember_last_opened_directory(self):
        folder = Folder.objects.create(name='remember me please')

        get_last_folder = lambda: self.client.get(reverse('admin:filer-directory_listing-last'), follow=True)

        self.client.get(reverse('admin:filer-directory_listing', kwargs={'folder_id': folder.id}))
        self.assertEqual(int(self.client.session['filer_last_folder_id']), folder.id)

        self.assertEqual(get_last_folder().context['folder'], folder)

        # let's test fallback
        folder.delete()
        self.assertTrue(isinstance(get_last_folder().context['folder'], FolderRoot))

    def test_filer_directory_listing_root_empty_get(self):
        response = self.client.post(reverse('admin:filer-directory_listing-root'))
        self.assertEqual(response.status_code, 200)

    def test_filer_directory_listing_root_get(self):
        create_folder_structure(depth=3, sibling=2, parent=None)
        response = self.client.post(reverse('admin:filer-directory_listing-root'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['folder'].children.count(), 6)

    def test_validate_no_duplcate_folders(self):
        FOLDER_NAME = "root folder 1"
        self.assertEqual(Folder.objects.count(), 0)
        response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'), {
                "name":FOLDER_NAME,
                "_popup": 1
                })
        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, FOLDER_NAME)
        # and create another one
        response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'),
                                    {"name":FOLDER_NAME, "_popup": 1})
        # second folder didn't get created
        self.assertEqual(Folder.objects.count(), 1)
        self.assertIn('Folder with this name already exists', response.content)

    def test_validate_no_duplcate_folders_on_rename(self):
        self.assertEqual(Folder.objects.count(), 0)
        response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'), {
                "name": "foo",
                "_popup": 1})
        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, "foo")
        # and create another one
        response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'), {
                "name": "bar",
                "_popup": 1})
        self.assertEqual(Folder.objects.count(), 2)
        bar = Folder.objects.get(name="bar")
        response = self.client.post("/admin/filer/folder/%d/" % bar.pk, {
                "name": "foo",
                "_popup": 1})
        self.assertIn('Folder with this name already exists', response.content)
        # refresh from db and validate that it's name didn't change
        bar = Folder.objects.get(pk=bar.pk)
        self.assertEqual(bar.name, "bar")

    def test_change_folder_owner_keep_name(self):
        folder = Folder.objects.create(name='foobar')
        another_superuser = User.objects.create_superuser(
            'gigi', 'admin@ignore.com', 'secret')
        response = self.client.post('/admin/filer/folder/%d/' % folder.pk, {
                'owner': another_superuser.pk,
                'name': 'foobar',
                '_continue': 'Save and continue editing'})
        # succesfful POST returns a redirect
        self.assertEqual(response.status_code, 302)
        folder = Folder.objects.get(pk=folder.pk)
        self.assertEqual(folder.owner.pk, another_superuser.pk)


class FilerImageAdminUrlsTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

    def tearDown(self):
        self.client.logout()


class FilerClipboardAdminUrlsTests(TestCase):
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
        for img in Image.objects.all():
            img.delete()

    def test_filer_upload_file(self, extra_headers={}):
        self.assertEqual(Image.objects.count(), 0)
        file_obj = django.core.files.File(open(self.filename))
        response = self.client.post(
            reverse('admin:filer-ajax_upload'),
            {'Filename': self.image_name, 'Filedata': file_obj, 'jsessionid': self.client.session.session_key,},
            **extra_headers
        )
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Image.objects.all()[0].original_filename, self.image_name)

    def test_filer_ajax_upload_file(self):
        self.assertEqual(Image.objects.count(), 0)
        file_obj = django.core.files.File(open(self.filename))
        response = self.client.post(
            reverse('admin:filer-ajax_upload')+'?filename=%s' % self.image_name,
            data=file_obj.read(),
            content_type='application/octet-stream',
            **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        )
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Image.objects.all()[0].original_filename, self.image_name)


class BulkOperationsMixin(object):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR,
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')
        self.create_src_and_dst_folders()
        self.folder = Folder.objects.create(name="root folder", parent=None)
        self.sub_folder1 = Folder.objects.create(name="sub folder 1", parent=self.folder)
        self.sub_folder2 = Folder.objects.create(name="sub folder 2", parent=self.folder)
        self.image_obj = self.create_image(self.src_folder)
        self.create_file(self.folder)
        self.create_file(self.folder)
        self.create_image(self.folder)
        self.create_image(self.sub_folder1)
        self.create_file(self.sub_folder1)
        self.create_file(self.sub_folder1)
        self.create_image(self.sub_folder2)
        self.create_image(self.sub_folder2)

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for f in File.objects.all():
            f.delete()
        for folder in Folder.objects.all():
            folder.delete()

    def create_src_and_dst_folders(self):
        self.src_folder = Folder(name="Src", parent=None)
        self.src_folder.save()
        self.dst_folder = Folder(name="Dst", parent=None)
        self.dst_folder.save()

    def create_image(self, folder, filename=None):
        filename = filename or 'test_image.jpg'
        file_obj = django.core.files.File(open(self.filename), name=filename)
        image_obj = Image.objects.create(owner=self.superuser, original_filename=self.image_name, file=file_obj, folder=folder)
        image_obj.save()
        return image_obj

    def create_file(self, folder, filename=None):
        filename = filename or 'test_file.dat'
        file_data = django.core.files.base.ContentFile('some data')
        file_data.name = filename
        file_obj = File.objects.create(owner=self.superuser, original_filename=filename, file=file_data, folder=folder)
        file_obj.save()
        return file_obj


class FilerBulkOperationsTests(BulkOperationsMixin, TestCase):
    def test_move_files_and_folders_action(self):
        # TODO: Test recursive (files and folders tree) move

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'move_files_and_folders',
            'post': 'yes',
            'destination': self.dst_folder.id,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 0)
        self.assertEqual(self.dst_folder.files.count(), 1)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.dst_folder.id,
        })
        response = self.client.post(url, {
            'action': 'move_files_and_folders',
            'post': 'yes',
            'destination': self.src_folder.id,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)

    def test_validate_no_duplicate_folders_on_move(self):
        """Create the following folder hierarchy:
        root
          |
          |--foo
          |   |-bar
          |
          |--bar
        
        and try to move the owter bar in foo. This has to fail since it would result
        in two folders with the same name and parent.
        """
        root = Folder.objects.create(name='root', owner=self.superuser)
        foo = Folder.objects.create(name='foo', parent=root, owner=self.superuser)
        bar = Folder.objects.create(name='bar', parent=root, owner=self.superuser)
        foos_bar = Folder.objects.create(name='bar', parent=foo, owner=self.superuser)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': root.pk,
        })
        response = self.client.post(url, {
            'action': 'move_files_and_folders',
            'post': 'yes',
            'destination': foo.pk,
            helpers.ACTION_CHECKBOX_NAME: 'folder-%d' % (bar.pk,),
        })
        # refresh from db and validate that it hasn't been moved
        bar = Folder.objects.get(pk=bar.pk)
        self.assertEqual(bar.parent.pk, root.pk)

    def test_move_to_clipboard_action(self):
        # TODO: Test recursive (files and folders tree) move

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'move_to_clipboard',
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 0)
        self.assertEqual(self.dst_folder.files.count(), 0)
        clipboard = Clipboard.objects.get(user=self.superuser)
        self.assertEqual(clipboard.files.count(), 1)
        tools.move_files_from_clipboard_to_folder(clipboard, self.src_folder)
        tools.discard_clipboard(clipboard)
        self.assertEqual(clipboard.files.count(), 0)
        self.assertEqual(self.src_folder.files.count(), 1)

    def test_files_set_public_action(self):
        self.image_obj.is_public = False
        self.image_obj.save()
        self.assertEqual(self.image_obj.is_public, False)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'files_set_public',
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.image_obj = Image.objects.get(id=self.image_obj.id)
        self.assertEqual(self.image_obj.is_public, True)

    def test_files_set_private_action(self):
        self.image_obj.is_public = True
        self.image_obj.save()
        self.assertEqual(self.image_obj.is_public, True)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'files_set_private',
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.image_obj = Image.objects.get(id=self.image_obj.id)
        self.assertEqual(self.image_obj.is_public, False)
        self.image_obj.is_public = True
        self.image_obj.save()

    def test_copy_files_and_folders_action(self):
        # TODO: Test recursive (files and folders tree) copy

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        self.assertEqual(self.image_obj.original_filename, 'test_file.jpg')
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'suffix': 'test',
            'destination': self.dst_folder.id,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 1)
        self.assertEqual(self.src_folder.files[0].id, self.image_obj.id)
        dst_image_obj = self.dst_folder.files[0]
        self.assertEqual(dst_image_obj.original_filename, 'test_filetest.jpg')

class FilerDeleteOperationTests(BulkOperationsMixin, TestCase):
    def test_delete_files_or_folders_action(self):
        self.assertNotEqual(File.objects.count(), 0)
        self.assertNotEqual(Image.objects.count(), 0)
        self.assertNotEqual(Folder.objects.count(), 0)
        url = reverse('admin:filer-directory_listing-root')
        folders = []
        for folder in FolderRoot().children.all():
            folders.append('folder-%d' % (folder.id,))
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: folders,
        })
        self.assertEqual(File.objects.count(), 0)
        self.assertEqual(Folder.objects.count(), 0)

    def test_delete_files_or_folders_action_with_mixed_types(self):
        # add more files/images so we can test the polymorphic queryset with multiple types
        self.create_file(folder=self.src_folder)
        self.create_image(folder=self.src_folder)
        self.create_file(folder=self.src_folder)

        self.assertNotEqual(File.objects.count(), 0)
        self.assertNotEqual(Image.objects.count(), 0)
        url = reverse('admin:filer-directory_listing', args=(self.folder.id,))
        folders = []
        for f in File.objects.filter(folder=self.folder):
            folders.append('file-%d' % (f.id,))
        folders.append('folder-%d' % self.sub_folder1.id)
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: folders,
            })
        self.assertEqual(File.objects.filter(folder__in=[self.folder.id, self.sub_folder1.id]).count(), 0)


class FilerResizeOperationTests(BulkOperationsMixin, TestCase):
    def test_resize_images_action(self):
        # TODO: Test recursive (files and folders tree) processing

        self.assertEqual(self.image_obj.width, 800)
        self.assertEqual(self.image_obj.height, 600)
        url = reverse('admin:filer-directory_listing', kwargs={
            'folder_id': self.src_folder.id,
        })
        response = self.client.post(url, {
            'action': 'resize_images',
            'post': 'yes',
            'width': 42,
            'height': 42,
            'crop': True,
            'upscale': False,
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.image_obj = Image.objects.get(id=self.image_obj.id)
        self.assertEqual(self.image_obj.width, 42)
        self.assertEqual(self.image_obj.height, 42)


class PermissionAdminTest(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

    def tearDown(self):
        self.client.logout()

    def test_render_add_view(self):
        """
        Really stupid and simple test to see if the add Permission view can be rendered
        """
        response = self.client.get(reverse('admin:filer_folderpermission_add'))
        self.assertEqual(response.status_code, 200)


class FolderListingTest(TestCase):

    def setUp(self):
        superuser = create_superuser()
        self.staff_user = User.objects.create_user(
            username='joe', password='x', email='joe@mata.com')
        self.staff_user.is_staff = True
        self.staff_user.save()
        self.parent = Folder.objects.create(name='bar', parent=None, owner=superuser)

        self.foo_folder = Folder.objects.create(name='foo', parent=self.parent, owner=self.staff_user)
        self.bar_folder = Folder.objects.create(name='bar', parent=self.parent, owner=superuser)
        self.baz_folder = Folder.objects.create(name='baz', parent=self.parent, owner=superuser)

        file_data = django.core.files.base.ContentFile('some data')
        file_data.name = 'spam'
        self.spam_file = File.objects.create(
            owner=superuser, original_filename='spam',
            file=file_data, folder=self.parent)
        self.client.login(username='joe', password='x')

    def test_with_permissions_disabled(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=False):
            response = self.client.get(
                reverse('admin:filer-directory_listing',
                        kwargs={'folder_id': self.parent.id}))
            item_list = response.context['paginated_items'].object_list
            # user sees all items: FOO, BAR, BAZ, SAMP
            self.assertEquals(
                set(folder.pk for folder in item_list),
                set([self.foo_folder.pk, self.bar_folder.pk, self.baz_folder.pk,
                     self.spam_file.pk]))

    def test_folder_ownership(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            response = self.client.get(
                reverse('admin:filer-directory_listing',
                        kwargs={'folder_id': self.parent.id}))
            item_list = response.context['paginated_items'].object_list
            # user sees only 1 folder : FOO
            # he doesn't see BAR, BAZ and SPAM because he doesn't own them
            # and no permission has been given
            self.assertEquals(
                set(folder.pk for folder in item_list),
                set([self.foo_folder.pk]))

    def test_with_permission_given_to_folder(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            # give permissions over BAR
            FolderPermission.objects.create(
                folder=self.bar_folder,
                user=self.staff_user,
                type=FolderPermission.THIS,
                can_edit=FolderPermission.ALLOW,
                can_read=FolderPermission.ALLOW,
                can_add_children=FolderPermission.ALLOW)
            response = self.client.get(
                reverse('admin:filer-directory_listing',
                        kwargs={'folder_id': self.parent.id}))
            item_list = response.context['paginated_items'].object_list
            # user sees 2 folder : FOO, BAR
            self.assertEquals(
                set(folder.pk for folder in item_list),
                set([self.foo_folder.pk, self.bar_folder.pk]))

    def test_with_permission_given_to_parent_folder(self):
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            FolderPermission.objects.create(
                folder=self.parent,
                user=self.staff_user,
                type=FolderPermission.CHILDREN,
                can_edit=FolderPermission.ALLOW,
                can_read=FolderPermission.ALLOW,
                can_add_children=FolderPermission.ALLOW)
            response = self.client.get(
                reverse('admin:filer-directory_listing',
                        kwargs={'folder_id': self.parent.id}))
            item_list = response.context['paginated_items'].object_list
            # user sees all items because he has permissions on the parent folder
            self.assertEquals(
                set(folder.pk for folder in item_list),
                set([self.foo_folder.pk, self.bar_folder.pk, self.baz_folder.pk,
                     self.spam_file.pk]))
