#-*- coding: utf-8 -*-
import os
import tempfile
import zipfile
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.core import files as dj_files
from django.contrib.admin import helpers, site
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group, Permission
from django.http import HttpRequest
from django.core.files import File as DjangoFile
from filer.models.filemodels import File
from filer.models.archivemodels import Archive
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.models.clipboardmodels import Clipboard
from filer.models.virtualitems import FolderRoot
from filer.models import tools
from filer.tests.helpers import (
    get_user_message, create_superuser, create_folder_structure,
    create_image, create_staffuser, create_folder_for_user, move_action,
    move_to_clipboard_action, paste_clipboard_to_folder, get_dir_listing_url,
    filer_obj_as_checkox, get_make_root_folder_url, enable_restriction,
    move_single_file_to_clipboard_action, SettingsOverride
)
from filer.utils.checktrees import TreeChecker
from filer import settings as filer_settings
from filer.utils.generate_filename import by_path
from cmsroles.models import Role
from cmsroles.tests.tests import HelpersMixin
from cmsroles.siteadmin import get_site_admin_required_permission
import json
from filer.admin import ClipboardAdmin


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
        response = self.client.get(get_make_root_folder_url() + "?_popup=1")
        self.assertEqual(response.status_code, 200)

    def test_filer_make_root_folder_post(self):
        FOLDER_NAME = "root folder 1"
        self.assertEqual(Folder.objects.count(), 0)
        data_to_post = {
             "name": FOLDER_NAME,
        }
        response = self.client.post(
            get_make_root_folder_url(),
            data_to_post)
        self.assertIn('Site is required', response.content)

        data_to_post['site'] = 1
        response = self.client.post(
            get_make_root_folder_url(),
            data_to_post)

        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, FOLDER_NAME)
        self.assertEqual(response.status_code, 302)

    def test_filer_directory_listing_root_empty_get(self):
        response = self.client.get(get_dir_listing_url(None))
        self.assertEqual(response.status_code, 200)

    def test_filer_directory_listing_root_get(self):
        create_folder_structure(depth=3, sibling=2, parent=None)
        response = self.client.get(get_dir_listing_url(None))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['folder'].children.count(), 6)

    def test_validate_no_duplcate_folders(self):
        FOLDER_NAME = "root folder 1"
        self.assertEqual(Folder.objects.count(), 0)
        post_data = {"name": FOLDER_NAME, "_popup": 1}
        response = self.client.post(
            get_make_root_folder_url(),
            post_data)
        self.assertIn('Site is required', response.content)
        post_data['site'] = 1
        response = self.client.post(
            get_make_root_folder_url(),
            post_data)
        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, FOLDER_NAME)
        # and create another one
        post_data = {"name": FOLDER_NAME, "_popup": 1}
        response = self.client.post(
            get_make_root_folder_url(),
            post_data)
        # second folder didn't get created
        self.assertEqual(Folder.objects.count(), 1)
        self.assertIn('folder name is already in use',
                      response.content)

    def test_validate_no_duplicate_folders_on_rename(self):
        self.assertEqual(Folder.objects.count(), 0)
        post_data = {"name": "foo", "_popup": 1}
        response = self.client.post(
            get_make_root_folder_url(),
            post_data)
        self.assertIn('Site is required', response.content)
        post_data['site'] = 1
        response = self.client.post(
            get_make_root_folder_url(),
            post_data)

        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, "foo")
        # and create another one
        post_data = {"name": "bar", "_popup": 1}
        response = self.client.post(
            get_make_root_folder_url(),
            post_data)
        self.assertIn('Site is required', response.content)

        post_data['site'] = 1
        response = self.client.post(
            get_make_root_folder_url(),
            post_data)

        self.assertEqual(Folder.objects.count(), 2)
        bar = Folder.objects.get(name="bar")
        response = self.client.post("/admin/filer/folder/%d/" % bar.pk, {
                "name": "foo",
                "_popup": 1})
        self.assertIn('folder name is already in use',
                      response.content)
        # refresh from db and validate that it's name didn't change
        bar = Folder.objects.get(pk=bar.pk)
        self.assertEqual(bar.name, "bar")

    def test_changelist_not_accessible(self):
        response = self.client.get("/admin/filer/file", follow=True)
        self.assertEqual(response.status_code, 403)

    def test_change_view_accessible(self):
        file1 = File.objects.create()
        response = self.client.get("/admin/filer/file/{}".format(file1.id), follow=True)
        self.assertEqual(response.status_code, 200)


class FilerImageAdminUrlsTests(TestCase):

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

    def test_changelist_not_accessible(self):
        response = self.client.get("/admin/filer/image", follow=True)
        self.assertEqual(response.status_code, 403)

    def test_change_view_accessible(self):
        image1 = Image.objects.create()
        response = self.client.get("/admin/filer/image/{}".format(image1.id), follow=True)
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        self.client.logout()


class FilerClipboardAdminUrlsTests(TestCase):

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
        for img in Image.objects.all():
            img.delete(to_trash=False)

    def test_filer_upload_image_no_extension(self):
        img_name = 'image_name'
        image = create_image()
        image_path = os.path.join(os.path.dirname(__file__), 'image_name')
        image.save(image_path, 'JPEG')
        file_obj = dj_files.File(open(image_path))
        self.assertEqual(Image.objects.count(), 0)
        response = self.client.post(
            reverse('admin:filer-ajax_upload'), {
            'Filename': img_name,
            'Filedata': file_obj,
            'jsessionid': self.client.session.session_key, },
        )
        self.assertEqual(Image.objects.count(), 1)
        img_obj = Image.objects.all()[0]
        self.assertEqual(img_obj.actual_name,
                         '{}_{}.jpeg'.format(img_obj.sha1[:10], img_name))
        os.remove(image_path)

    def test_filer_upload_file(self, extra_headers={}):
        self.assertEqual(Image.objects.count(), 0)
        file_obj = dj_files.File(open(self.filename))
        response = self.client.post(
            reverse('admin:filer-ajax_upload'), {
            'Filename': self.image_name,
            'Filedata': file_obj,
            'jsessionid': self.client.session.session_key, },
            **extra_headers
        )
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Image.objects.all()[0].original_filename,
                         self.image_name)

    def test_file_upload_no_duplicate_files(self, extra_headers={}):
        self.assertEqual(Image.objects.count(), 0)
        file_obj = dj_files.File(open(self.filename))
        response = self.client.post(
            reverse('admin:filer-ajax_upload'), {
            'Filename': self.image_name,
            'Filedata': file_obj,
            'jsessionid': self.client.session.session_key, },
            **extra_headers
        )
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Image.objects.all()[0].original_filename,
                         self.image_name)
        self.assertEqual(Clipboard.objects.count(), 1)
        clip = Clipboard.objects.get(id=1) # there is(or should be) just one clipboard
        self.assertEqual(clip.files.count(), 1)
        # upload the same file again. This must fail since the
        # clipboard can't contain two files with the same name
        response = self.client.post(
            reverse('admin:filer-ajax_upload'), {
            'Filename': self.image_name,
            'Filedata': file_obj,
            'jsessionid': self.client.session.session_key, },
            **extra_headers
        )
        self.assertEqual(Image.objects.count(), 1)
        self.assertIn('error', response.content)
        errormsg = ClipboardAdmin.messages['already-exists'].format(self.image_name)
        self.assertIn(errormsg, response.content)
        self.assertEqual(clip.files.count(), 1)

    def test_paste_from_clipboard_no_duplicate_files(self):
        first_folder = Folder.objects.create(
            name='first', site=Site.objects.get(id=1))

        def upload():
            file_obj = dj_files.File(open(self.filename))
            response = self.client.post(
                reverse('admin:filer-ajax_upload'),
                {'Filename': self.image_name, 'Filedata': file_obj,
                 'jsessionid': self.client.session.session_key, })
            return Image.objects.all().order_by('-id')[0]

        uploaded_image = upload()
        self.assertEqual(uploaded_image.original_filename, self.image_name)

        def paste(uploaded_image):
            # current user should have one clipboard created
            clipboard = self.superuser.filer_clipboard
            response = self.client.post(
                reverse('admin:filer-paste_clipboard_to_folder'),
                {'folder_id': first_folder.pk,
                 'clipboard_id': clipboard.pk})
            return Image.objects.get(pk=uploaded_image.pk)

        pasted_image = paste(uploaded_image)
        self.assertEqual(pasted_image.folder.pk, first_folder.pk)
        # upload and paste the same image again
        second_upload = upload()
        # second paste failed due to name conflict
        second_pasted_image = paste(second_upload)
        clipboard = self.superuser.filer_clipboard
        # file should remain in clipboard and should not be located in
        #   destination folder
        self.assertEqual(clipboard.files.count(), 1)
        self.assertEqual(second_pasted_image.folder, None)

    def test_filer_ajax_upload_file(self):
        self.assertEqual(Image.objects.count(), 0)
        file_obj = dj_files.File(open(self.filename))
        response = self.client.post(reverse('admin:filer-ajax_upload') +
            '?filename=%s' % self.image_name,
            data=file_obj.read(),
            content_type='application/octet-stream',
            **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        )
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Image.objects.all()[0].original_filename,
                         self.image_name)

    def test_filer_ajax_upload_long_filename(self):
        # additional setup
        # create an image with a long filename
        long_image_name = 'test' * 26 + '.jpg' # length of 104 title + 4 extension
        filename = os.path.join(os.path.dirname(__file__), long_image_name)
        long_name_img = create_image()
        long_name_img.save(filename, 'JPEG')

        # preconditions: before upload
        self.assertEqual(Image.objects.count(), 0)

        # try to upload
        file_obj = dj_files.File(open(filename))
        response = self.client.post(reverse('admin:filer-ajax_upload') +
                                    '?filename=%s' % long_image_name,
                                    data=file_obj.read(),
                                    content_type='application/octet-stream',
                                    **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
                                   )
        # upload succedes
        self.assertEqual(Image.objects.count(), 1)
        # but title is not the long one
        self.assertTrue(Image.objects.first().original_filename != long_image_name)
        # it is first 100 characters
        self.assertTrue(Image.objects.first().original_filename == 'test' * 25 + '.jpg')

        # additional tear down
        os.remove(filename)


class BulkOperationsMixin(object):

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')
        self.create_src_and_dst_folders()
        self.folder = Folder.objects.create(name="root folder", parent=None)
        self.sub_folder1 = Folder.objects.create(
            name="sub folder 1", parent=self.folder)
        self.sub_folder2 = Folder.objects.create(
            name="sub folder 2", parent=self.folder)
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
            f.delete(to_trash=False)
        for folder in Folder.objects.all():
            folder.delete(to_trash=False)

    def create_src_and_dst_folders(self):
        site = Site.objects.get(id=1)
        self.src_folder = Folder(name="Src", parent=None, site=site)
        self.src_folder.save()
        self.dst_folder = Folder(name="Dst", parent=None, site=site)
        self.dst_folder.save()

    def create_image(self, folder, filename=None):
        filename = filename or 'test_image.jpg'
        file_obj = dj_files.File(open(self.filename), name=filename)
        image_obj = Image.objects.create(
            owner=self.superuser, original_filename=self.image_name,
            file=file_obj, folder=folder)
        image_obj.save()
        return image_obj

    def create_file(self, folder, filename=None):
        filename = filename or 'test_file.dat'
        file_data = dj_files.base.ContentFile('some data')
        file_data.name = filename
        file_obj = File.objects.create(owner=self.superuser,
            original_filename=filename, file=file_data, folder=folder)
        file_obj.save()
        return file_obj


@SettingsOverride(filer_settings,
    FILER_PUBLICMEDIA_UPLOAD_TO=by_path, FOLDER_AFFECTS_URL=True)
class FilerBulkOperationsTests(BulkOperationsMixin, TestCase):

    def test_move_files_and_folders_action(self):
        # TODO: Test recursive (files and folders tree) move

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        response, _ = move_action(
            self.client, self.src_folder, self.dst_folder, [self.image_obj])
        self.assertEqual(self.src_folder.files.count(), 0)
        self.assertEqual(self.dst_folder.files.count(), 1)

        response, _ = move_action(
            self.client, self.dst_folder, self.src_folder, [self.image_obj])
        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)

    def test_validate_no_duplicate_folders_on_move(self):
        """ move file from foo to bar
          foo
          |--file
          bar
          |--file
        """
        foo = Folder.objects.create(name='foo', site=Site.objects.get(id=1))
        bar = Folder.objects.create(name='bar', site=Site.objects.get(id=1))
        file_foo = File.objects.create(
            original_filename='file', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        file_bar = File.objects.create(
            original_filename='file', folder=bar,
            file=dj_files.base.ContentFile('some data'))

        response, url = move_action(
            self.client, foo, bar, [file_foo], follow=True)
        self.assertRedirects(response, url)
        self.assertIn(
            "already exist at the selected destination",
            get_user_message(response).message)

        foo = Folder.objects.get(id=foo.id)
        file_foo = File.objects.get(id=file_foo.id)
        self.assertEqual(foo.files.count(), 1)
        self.assertEqual(file_foo.parent.id, foo.id)

        bar = Folder.objects.get(id=bar.id)
        file_bar = File.objects.get(id=file_bar.id)
        self.assertEqual(bar.files.count(), 1)
        self.assertEqual(file_bar.parent.id, bar.id)

    def test_validate_no_duplicate_folders_on_move(self):
        """Create the following folder hierarchy:
        root
          |
          |--foo
          |   |-bar
          |
          |--bar

        and try to move the owter bar in foo. This has to fail since it
        would result in two folders with the same name and parent.
        """
        root = Folder.objects.create(name='root', owner=self.superuser)
        foo = Folder.objects.create(
            name='foo', parent=root, owner=self.superuser)
        bar = Folder.objects.create(
            name='bar', parent=root, owner=self.superuser)
        foos_bar = Folder.objects.create(
            name='bar', parent=foo, owner=self.superuser)
        url = get_dir_listing_url(root)

        response, _ = move_action(self.client, root, foo, [bar])
        # refresh from db and validate that it hasn't been moved
        bar = Folder.objects.get(pk=bar.pk)
        self.assertEqual(bar.parent.pk, root.pk)

    def test_move_to_clipboard_action(self):
        # TODO: Test recursive (files and folders tree) move

        self.assertEqual(self.src_folder.files.count(), 1)
        self.assertEqual(self.dst_folder.files.count(), 0)
        url = get_dir_listing_url(self.src_folder)
        response = move_to_clipboard_action(
            self.client, self.src_folder, [self.image_obj])
        self.assertEqual(self.src_folder.files.count(), 0)
        self.assertEqual(self.dst_folder.files.count(), 0)
        clipboard = Clipboard.objects.get(user=self.superuser)
        self.assertEqual(clipboard.files.count(), 1)
        request = HttpRequest()
        tools.move_files_from_clipboard_to_folder(
            request, clipboard, self.src_folder)
        tools.discard_clipboard(clipboard)
        self.assertEqual(clipboard.files.count(), 0)
        self.assertEqual(self.src_folder.files.count(), 1)

    def test_files_set_public_action(self):
        return
        self.image_obj.is_public = False
        self.image_obj.save()
        self.assertEqual(self.image_obj.is_public, False)
        url = get_dir_listing_url(self.src_folder)
        response = self.client.post(url, {
            'action': 'files_set_public',
            helpers.ACTION_CHECKBOX_NAME: 'file-%d' % (self.image_obj.id,),
        })
        self.image_obj = Image.objects.get(id=self.image_obj.id)
        self.assertEqual(self.image_obj.is_public, True)

    def test_files_set_private_action(self):
        return
        self.image_obj.is_public = True
        self.image_obj.save()
        self.assertEqual(self.image_obj.is_public, True)
        url = get_dir_listing_url(self.src_folder)
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
        url = get_dir_listing_url(self.src_folder)
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
        self.assertTrue(os.path.exists(
            File.objects.get(id=dst_image_obj.id).file.path))
        self.assertTrue(os.path.exists(
            File.objects.get(id=self.image_obj.id).file.path))

    def test_copy_recursion_error(self):
        ## it's enough to try to move/copy to itself with no error
        ## this means the operation error is caught
        url = get_dir_listing_url(None)
        response = self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'suffix': 'test',
            'destination': self.src_folder.id,
            helpers.ACTION_CHECKBOX_NAME:
                filer_obj_as_checkox(self.src_folder),
        })
        response = self.client.post(url, {
            'action': 'move_files_and_folders',
            'post': 'yes',
            'destination': self.src_folder.id,
            helpers.ACTION_CHECKBOX_NAME:
                filer_obj_as_checkox(self.src_folder),
        }, follow=True)


class FilerDeleteOperationTests(BulkOperationsMixin, TestCase):

    def test_delete_files_or_folders_action(self):
        file_count = File.objects.count()
        folder_count = Folder.objects.count()
        self.assertNotEqual(file_count, 0)
        self.assertNotEqual(folder_count, 0)
        url = get_dir_listing_url(None)
        folders = []
        for folder in FolderRoot().children.all():
            folders.append('folder-%d' % (folder.id,))
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: folders,
        })
        self.assertEqual(File.objects.count(), 0)
        self.assertEqual(File.trash.count(), file_count)
        self.assertEqual(Folder.objects.count(), 0)
        self.assertEqual(Folder.trash.count(), folder_count)

    def test_delete_files_or_folders_action_with_mixed_types(self):
        # add more files/images so we can test the polymorphic queryset
        # with multiple types
        self.create_file(folder=self.src_folder)
        self.create_image(folder=self.src_folder)
        self.create_file(folder=self.src_folder)
        qs = File.objects.filter(
            folder__in=[self.folder.id, self.sub_folder1.id])
        file_count = qs.count()

        url = get_dir_listing_url(self.folder)
        items_to_delete = []
        for f in File.objects.filter(folder=self.folder):
            items_to_delete.append('file-%d' % (f.id,))
        items_to_delete.append('folder-%d' % self.sub_folder1.id)
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: items_to_delete,
            })

        alive_files = qs.count()
        self.assertEqual(alive_files, 0)
        self.assertEqual(File.trash.count(), file_count - alive_files)


class FilerResizeOperationTests(BulkOperationsMixin, TestCase):

    def test_resize_images_action(self):
        # TODO: Test recursive (files and folders tree) processing
        self.assertEqual(self.image_obj.width, 800)
        self.assertEqual(self.image_obj.height, 600)
        # since the 'resize' action is disabled from the admin
        return
        url = get_dir_listing_url(self.src_folder.id)
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


class BaseTestFolderTypePermissionLayer(object):

    def test_default_add_view_is_forbidden(self):
        response = self.client.get(reverse('admin:filer_folder_add'))
        self.assertEqual(response.status_code, 403)

    def test_change_child_site_folder(self):
        f1 = Folder.objects.create(name='foo', site=Site.objects.get(id=1))
        f2 = Folder.objects.create(name='foo_bar', parent=f1)
        # regular users should be able to change child folders
        response = self.client.get(
            reverse('admin:filer_folder_change', args=(f2.pk, )))
        self.assertEqual(response.status_code, 200)
        self.assertIn('adminform', response.context_data)
        # make sure the folder that is going to be saved is a site folder
        form = response.context_data['adminform'].form
        self.assertEqual(form.instance.folder_type, Folder.SITE_FOLDER)
        self.assertItemsEqual(sorted(['name', 'restricted']),
                              sorted(form.fields.keys()))
        # check if save worked
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(f2.pk, )), {
                'name': 'foo_bar__changed'
            })
        self.assertEqual(response.status_code, 302)
        f2__changed = Folder.objects.get(id=f2.pk)
        self.assertEqual(f2__changed.name, 'foo_bar__changed')
        self.assertEqual(f2__changed.folder_type, Folder.SITE_FOLDER)

    def test_add_core_folder(self):
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)
        f2 = Folder.objects.create(
            name='foo_bar', parent=f1, folder_type=Folder.CORE_FOLDER)
        self.assertEqual(f1.folder_type, Folder.CORE_FOLDER)
        self.assertEqual(f2.folder_type, Folder.CORE_FOLDER)
        url = get_make_root_folder_url()
        response = self.client.get(url,{
            'parent_id': f2.id
            })
        self.assertEqual(response.status_code, 403)

        response = self.client.post(url,{
            'parent_id': f2.id,
            'name': 'foo_bar_core'
            })
        self.assertEqual(response.status_code, 403)

    def test_change_core_folder(self):
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)
        f2 = Folder.objects.create(
            name='foo_bar', parent=f1, folder_type=Folder.CORE_FOLDER)
        self.assertEqual(f1.folder_type, Folder.CORE_FOLDER)
        self.assertEqual(f2.folder_type, Folder.CORE_FOLDER)
        # No one should be able to change core folders
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(f2.pk, )),
            {'post': ['yes']})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(f1.pk, )),
            {'post': ['yes']})
        self.assertEqual(response.status_code, 403)

    def test_delete_child_site_folder(self):
        f1 = Folder.objects.create(name='foo', site=Site.objects.get(id=1))
        f2 = Folder.objects.create(name='bar', parent=f1)
        f3 = Folder.objects.create(name='baz', parent=f1)
        # regular users should be able to delete child site folders
        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(f2.pk, )),
            {'post': ['yes']})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Folder.objects.filter(id=f2.id).count(), 0)

        response = self.client.post(get_dir_listing_url(f1), {
                'action': 'delete_files_or_folders',
                'post': 'yes',
                helpers.ACTION_CHECKBOX_NAME: ['folder-%d' % f3.id],
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Folder.objects.filter(id=f3.id).count(), 0)

    def test_delete_child_core_folder(self):
        f1 = Folder.objects.create(name='foo', folder_type=Folder.CORE_FOLDER)
        f2 = Folder.objects.create(name='bar', parent=f1)
        f3 = Folder.objects.create(name='bazbazbazbaz', parent=f1)
        self.assertEqual(Folder.objects.get(id=f1.id).is_core(), True)
        self.assertEqual(Folder.objects.get(id=f2.id).is_core(), True)
        self.assertEqual(Folder.objects.get(id=f3.id).is_core(), True)
        # regular users should not be able to delete child core folders
        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(f2.pk, )),
            {'post': ['yes']})
        self.assertEqual(Folder.objects.filter(id=f2.id).count(), 1)

        response = self.client.post(get_dir_listing_url(f1), {
                'action': 'delete_files_or_folders',
                'post': 'yes',
                helpers.ACTION_CHECKBOX_NAME: filer_obj_as_checkox(f3),
        })
        self.assertEqual(Folder.objects.filter(id=f3.id).count(), 1)

    def test_add_root_folder(self):
        # superusers should be able to add only root site folders
        response = self.client.get(
            get_make_root_folder_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn('adminform', response.context_data)
        # make sure the folder that is going to be saved is a site folder
        form = response.context_data['adminform'].form
        self.assertEqual(form.instance.folder_type, Folder.SITE_FOLDER)
        # only fields 'site', 'name' should be visible
        expected_fields = ['site', 'name']
        if self.user.is_superuser:
            expected_fields.append('shared')
        self.assertItemsEqual(sorted(expected_fields),
                              sorted(form.fields.keys()))

        s1, _ = Site.objects.get_or_create(
            name='foo_site', domain='foo-domain.com')
        response = self.client.post(
            get_make_root_folder_url(),
            {'name': 'foo', 'site': s1.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Folder.objects.count(), 1)

    def test_change_root_core_folder(self):
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)
        response = self.client.get(
            reverse('admin:filer_folder_change', args=(f1.pk, )))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(f1.pk, )), {})
        self.assertEqual(response.status_code, 403)

    def test_change_root_site_folder(self):
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.SITE_FOLDER)
        response = self.client.get(
            reverse('admin:filer_folder_change', args=(f1.pk, )))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(f1.pk, )), {})
        self.assertEqual(response.status_code, 200)

    def test_delete_root_core_folder(self):
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)

        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(f1.pk, )),
            {'post': 'yes'})
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)
        response = self.client.post(
            get_dir_listing_url(None), {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: ['folder-%d' % f1.id],
        })
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)

    def test_delete_root_site_folder(self):
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.SITE_FOLDER,
            site=Site.objects.get(id=1))
        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(f1.pk, )),
            {'post': 'yes'})
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 0)
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.SITE_FOLDER,
            site=Site.objects.get(id=1))
        response = self.client.post(
            get_dir_listing_url(None), {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: ['folder-%d' % f1.id],
        })
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 0)

    def _build_some_folder_structure(self, folder_type, site):
        _folders, _files = {}, {}
        foo1 = Folder.objects.create(
            name='foo1', folder_type=folder_type, site=site)
        _folders['foo1'] = foo1
        foo2 = Folder.objects.create(
            name='foo2', folder_type=folder_type, site=site)
        _folders['foo2'] = foo2
        bar = Folder.objects.create(
            name='bar', folder_type=folder_type, parent=foo1, site=site)
        _folders['bar'] = bar
        baz1 = Folder.objects.create(
            name='baz1', folder_type=folder_type, parent=bar, site=site)
        _folders['baz1'] = baz1
        baz2 = Folder.objects.create(
            name='baz2', folder_type=folder_type, parent=bar, site=site)
        _folders['baz2'] = baz2

        file_bar = File.objects.create(
            original_filename='bar_file', folder=bar,
            file=dj_files.base.ContentFile('some data'))
        _files['file_bar'] = file_bar
        return _folders, _files

    def test_move_core_folders(self):
        folders, files = self._build_some_folder_structure(
            Folder.CORE_FOLDER, None)

        response, _ = move_action(
            self.client, folders['bar'], folders['foo2'], [folders['baz1']])
        assert Folder.objects.filter(parent=folders['foo2']).count() == 0

    def test_move_site_folder_to_core_destination_folder(self):
        folders, files = self._build_some_folder_structure(
            Folder.SITE_FOLDER, Site.objects.get(id=1))
        f1 = Folder.objects.create(
            name='destination', folder_type=Folder.CORE_FOLDER)
        response, _ = move_action(
            self.client, folders['bar'], f1, [folders['baz1']])
        assert Folder.objects.filter(parent=f1).count() == 0
        f1.delete(to_trash=False)
        return folders, files

    def _get_clipboard_files(self):
        clipboard, _ = Clipboard.objects.get_or_create(
            user=self.user)
        return clipboard.files

    def test_move_to_clipboard_from_root(self):
        file_foo = File.objects.create(
            original_filename='foo', folder=None,
            file=dj_files.base.ContentFile('some data'))
        self.assertEqual(
            self._get_clipboard_files().count(), 0)

        move_to_clipboard_action(self.client, 'unfiled', [file_foo])
        self.assertEqual(
            self._get_clipboard_files().count(), 1)

        file_bar = File.objects.create(
            original_filename='bar', folder=None,
            file=dj_files.base.ContentFile('some data'))
        move_single_file_to_clipboard_action(
            self.client, 'unfiled', [file_bar])
        self.assertEqual(
            self._get_clipboard_files().count(), 2)

    def test_move_to_clipboard_from_site_folders(self):
        foo = Folder.objects.create(name='foo', site=Site.objects.get(id=1))
        file_foo = File.objects.create(
            original_filename='foo', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        self.assertEqual(
            self._get_clipboard_files().count(), 0)

        move_to_clipboard_action(self.client, None, [foo])
        self.assertEqual(
            self._get_clipboard_files().count(), 0)

        file_bar = File.objects.create(
            original_filename='bar', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        move_to_clipboard_action(self.client, foo, [file_bar])
        self.assertEqual(
            self._get_clipboard_files().count(), 1)

        file_baz = File.objects.create(
            original_filename='baz', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        move_single_file_to_clipboard_action(
            self.client, foo, [file_baz])
        self.assertEqual(
            self._get_clipboard_files().count(), 2)

    def test_move_to_clipboard_from_core_folders(self):
        foo = Folder.objects.create(name='foo',
                                    folder_type=Folder.CORE_FOLDER)
        file_foo = File.objects.create(
            original_filename='foo_file', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        self.assertEqual(
            self._get_clipboard_files().count(), 0)
        response, _ = move_to_clipboard_action(self.client, None, [foo])
        self.assertEqual(
            self._get_clipboard_files().count(), 0)
        response, _ = move_to_clipboard_action(self.client, foo, [file_foo])
        # actions are not available if current view is core folder
        self.assertEqual(
            self._get_clipboard_files().count(), 0)

        response = move_single_file_to_clipboard_action(
            self.client, foo, [file_foo])
        self.assertEqual(
            self._get_clipboard_files().count(), 0)

    def test_move_from_clipboard_to_root(self):
        bar_file = File.objects.create(
            original_filename='bar_file',
            file=dj_files.base.ContentFile('some data'))
        clipboard, _ = Clipboard.objects.get_or_create(
            user=self.user)
        clipboard.append_file(bar_file)
        self.assertEqual(
            self._get_clipboard_files().count(), 1)
        response = paste_clipboard_to_folder(
            self.client, None, clipboard)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self._get_clipboard_files().count(), 1)

    def test_move_from_clipboard_to_core_folders(self):
        bar_file = File.objects.create(
            original_filename='bar_file',
            file=dj_files.base.ContentFile('some data'))
        core_folder = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)
        clipboard, _ = Clipboard.objects.get_or_create(
            user=self.user)
        clipboard.append_file(bar_file)
        self.assertEqual(
            self._get_clipboard_files().count(), 1)
        response = paste_clipboard_to_folder(
            self.client, core_folder, clipboard)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self._get_clipboard_files().count(), 1)

    def test_move_from_clipboard_to_site_folders(self):
        bar_file = File.objects.create(
            original_filename='bar_file',
            file=dj_files.base.ContentFile('some data'))
        site_folder = Folder.objects.create(
            name='foo', site=Site.objects.get(id=1))
        clipboard, _ = Clipboard.objects.get_or_create(
            user=self.user)
        clipboard.append_file(bar_file)
        self.assertEqual(
            self._get_clipboard_files().count(), 1)
        response = paste_clipboard_to_folder(
            self.client, site_folder, clipboard)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self._get_clipboard_files().count(), 0)
        self.assertEqual(len(site_folder.files), 1)

    def test_message_error_move_root_folder(self):
        site = Site.objects.get(id=1)
        foo = Folder.objects.create(name='foo', site=site)
        bar = Folder.objects.create(name='bar', site=site)
        response, url = move_action(
            self.client, None, foo, [bar], follow=True)
        if self.user.is_superuser:
            self.assertIn(
                "not allowed to move root folders",
                get_user_message(response).message)
        else:
            self.assertIn(
                "No action selected.",
                get_user_message(response).message)

    def test_message_error_user_no_site_on_move(self):
        site = Site.objects.get(id=1)
        foo_root = Folder.objects.create(name='foo_root')
        foo = Folder.objects.create(name='foo', parent=foo_root)
        bar = Folder.objects.create(name='bar', site=site)
        response, url = move_action(
            self.client, foo_root, bar, [foo], follow=True)
        self.assertRedirects(response, url)
        self.assertIn(
            "Some of the selected files/folders do not belong to any site.",
            get_user_message(response).message)

    def test_message_error_user_sites_mismatch_on_move(self):
        site = Site.objects.get(id=1)
        other_site, _ = Site.objects.get_or_create(
            name='foo_site', domain='foo-domain.com')
        # make a root for foo in order to work for regular users
        foo_root = Folder.objects.create(name='foo_root', site=other_site)
        foo = Folder.objects.create(name='foo', parent=foo_root)
        bar = Folder.objects.create(name='bar11', site=site)
        url = get_dir_listing_url(foo_root)
        response, url = move_action(
            self.client, foo_root, bar, [foo], follow=True)
        self.assertRedirects(response, url)
        self.assertIn(
            "Selected files/folders need to belong to the same site as the "
            "destination folder.",
            get_user_message(response).message)

    def test_destination_no_site_on_move(self):
        site = Site.objects.get(id=1)
        foo = Folder.objects.create(name='foo')
        bar = Folder.objects.create(name='bar', site=site)
        baz = Folder.objects.create(name='baz', site=site, parent=bar)
        response, url = move_action(self.client, bar, foo, [baz])
        assert Folder.objects.filter(parent=foo.id).count() == 0

    def test_folder_destination_filtering(self):
        orphaned = Folder.objects.create(name='orphaned')
        core = Folder.objects.create(
            name='core', folder_type=Folder.CORE_FOLDER)
        foo = Folder.objects.create(
            name='foo', site=Site.objects.get(id=1))
        selected = Folder.objects.create(
            parent=foo, name='selected', site=Site.objects.get(id=1))
        file_in_selected = File.objects.create(
            folder=selected, original_filename='file_in_selected',
            file=dj_files.base.ContentFile('some data'))
        valid_destination = Folder.objects.create(
            parent=foo, name='valid', site=Site.objects.get(id=1))

        def _fetch_destinations(parent):
            url = reverse('admin:filer-destination_folders')
            tree_data = json.loads(
                self.client.get(
                    url, {
                        'parent': parent,
                        'selected_folders': json.dumps([selected.pk]),
                        'current_folder': foo.pk
                    }, **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
                ).content)
            return {int(el['key']): el for el in tree_data}

        root_destinations = _fetch_destinations('null')
        assert root_destinations.keys() == [foo.id]
        assert root_destinations[foo.id]['unselectable'] == True
        foo_destinations = _fetch_destinations(foo.pk)
        assert foo_destinations.keys() == [valid_destination.id]
        assert foo_destinations[valid_destination.id]['unselectable'] == False

    def test_move_from_unfiled(self):
        foo_file = File.objects.create(
            original_filename='foo_file',
            file=dj_files.base.ContentFile('some data'))
        bar = Folder.objects.create(
            name='bar', site=Site.objects.get(id=1))
        response, url = move_action(self.client, 'unfiled', bar, [foo_file])
        self.assertEqual(File.objects.filter(folder=bar).count(), 1)
        self.assertEqual(File.objects.filter(folder__isnull=True).count(), 0)

    def test_copy_site_folder_to_core_destination_folder(self):
        folders, files = self._build_some_folder_structure(
            Folder.SITE_FOLDER, Site.objects.get(id=1))
        f1 = Folder.objects.create(
            name='destination', folder_type=Folder.CORE_FOLDER)

        url = get_dir_listing_url(None)
        response = self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'destination': f1.id,
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(folders['bar'])]})

        assert "The selected destination was not valid, so the selected files and folders "\
            "were not copied. Please try again." in response.cookies['messages'].value,\
            "Warning message not found in wrong copy response"
        return folders, files

    def test_file_from_core_folder_is_unchangeable(self):
        f1 = Folder.objects.create(name='foo', folder_type=Folder.CORE_FOLDER)
        file1 = File.objects.create(
            original_filename='bar_file', folder=f1,
            file=dj_files.base.ContentFile('some data'))
        url = reverse('admin:filer_file_change', args=(file1.id, ))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('submit', response.content)
        self.assertNotIn('delete/', response.content)
        # only one input(csrfmiddlewaretoken) the rest are readonly fields
        self.assertEqual(response.content.count('<input'), 1)

    def test_file_from_site_folder_is_changeable(self):
        f1 = Folder.objects.create(name='foo', site=Site.objects.get(id=1))
        file1 = File.objects.create(
            original_filename='bar_file', folder=f1,
            file=dj_files.base.ContentFile('some data'))
        url = reverse('admin:filer_file_change', args=(file1.id, ))
        response = self.client.get(url)
        self.assertIn('submit', response.content)
        self.assertIn('delete/', response.content)
        # at least the choose file and csrfmiddlewaretoken
        self.assertGreater(response.content.count('<input'), 2)

    def _build_files_structure_for_archive(self):
        file_structure = {}
        file_structure['foo'] = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)
        file_structure['bar'] = Folder.objects.create(
            name='bar', site=Site.objects.get(id=1))
        file_structure['foo_file'] = Archive.objects.create(
            original_filename='foo_file.zip', folder=file_structure['foo'],
            file=dj_files.base.ContentFile('zippy'))
        file_structure['bar_file'] = Archive.objects.create(
            original_filename='bar_file.zip', folder=file_structure['bar'],
            file=dj_files.base.ContentFile('zippy'))
        file_structure['baz_file'] = Archive.objects.create(
            original_filename='baz_file.zip',
            file=dj_files.base.ContentFile('zippy'))
        return file_structure

    def test_extract_files_in_core_folder(self):
        files = self._build_files_structure_for_archive()
        url = get_dir_listing_url(files['foo'])
        assert Folder.objects.get(id=files['foo'].id).files.count() == 1
        response = self.client.post(url, {
            'action': 'extract_files',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(files['foo_file'])]})
        # will not get extracted since no actions available in core folders
        assert Folder.objects.get(id=files['foo'].id).files.count() == 1

    def test_extract_files_in_site_folder(self):
        files = self._build_files_structure_for_archive()
        url = get_dir_listing_url(files['bar'])
        response = self.client.post(url, {
            'action': 'extract_files',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(files['bar_file'])]}, follow=True)
        self.assertEqual(get_user_message(response).message,
                         'bar_file.zip is not a valid zip file')

    def test_extract_in_unfiled_folder(self):
        files = self._build_files_structure_for_archive()
        url = get_dir_listing_url('unfiled')
        count_in_unfiled = File.objects.filter(folder__isnull=True).count()
        response = self.client.post(url, {
            'action': 'extract_files',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(files['baz_file'])]})
        assert count_in_unfiled == File.objects.filter(
            folder__isnull=True).count()


class TestFolderTypePermissionForSuperUser(
    TestCase, BaseTestFolderTypePermissionLayer):

    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_superuser = user.is_staff = user.is_active = True
        user.save()
        user.user_permissions = Permission.objects.all()
        self.client.login(username=username, password=password)
        self.user = user

    def test_restriction_change(self):
        site = Site.objects.get(id=1)
        foo_root = Folder.objects.create(name='foo_root')
        unfiled_file = File.objects.create(name='unfiled_file', folder=foo_root, restricted=False)
        response, url = enable_restriction(
            self.client, foo_root, [unfiled_file], follow=False)
        assert "Successfully enabled restriction for 1 files and/or folders."\
            in response.cookies['messages'].value,\
            "Operation was expected to fail."


class TestFolderTypePermissionLayerForRegularUser(
    TestCase, BaseTestFolderTypePermissionLayer):

    def _user_setup(self, user):
        foo_base_group = Group.objects.create(name='foo_base_group')
        filer_perms = Permission.objects.filter(
            content_type__app_label='filer')
        foo_base_group.permissions = filer_perms
        foo_base_group.save()
        developer_role = Role.objects.create(
            name='foo_role', group=foo_base_group,
            is_site_wide=True)
        other_site, _ = Site.objects.get_or_create(
            name='foo_site', domain='foo-domain.com')
        developer_role.grant_to_user(user, Site.objects.get(id=1))
        developer_role.grant_to_user(user, other_site)

    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_staff = user.is_active = True
        user.save()
        self._user_setup(user)
        self.client.login(username=username, password=password)
        self.user = user

    def _make_user_site_admin(self):
        base_group = Group.objects.get(name='foo_base_group')
        base_group.permissions.add(get_site_admin_required_permission())

    def test_add_root_folder_for_site_admins(self):
        # site admins should be able to do this the same as superusers
        # add site admin perm to make the current user a site admin
        self._make_user_site_admin()
        self_cls = TestFolderTypePermissionLayerForRegularUser
        super(self_cls, self).test_add_root_folder()

    def test_add_root_folder(self):
        # regular users should not be able to add root folders at all
        response = self.client.get(
            get_make_root_folder_url())
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            get_make_root_folder_url(), {})
        self.assertEqual(response.status_code, 403)

    def test_change_root_site_folder(self):
        # regular users should not be able to change root folders at all
        f1 = Folder.objects.create(name='foo', folder_type=Folder.SITE_FOLDER)
        response = self.client.get(
            reverse('admin:filer_folder_change', args=(f1.pk, )))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(f1.pk, )), {})
        self.assertEqual(response.status_code, 403)

    def test_delete_root_core_folder(self):
        f1 = Folder.objects.create(
            name='foo', site=Site.objects.get(id=1),
            folder_type=Folder.SITE_FOLDER)
        # regular users should not be able to delete root folders at all
        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(f1.pk, )),
            {'post': 'yes'})
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)

        response = self.client.post(
            get_dir_listing_url(None), {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: ['folder-%d' % f1.id],
        })
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)

    def test_delete_root_site_folder(self):
        f1 = Folder.objects.create(
            name='foo', folder_type=Folder.CORE_FOLDER)
        # regular users should not be able to delete root folders at all
        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(f1.pk, )),
            {'post': 'yes'})
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)

        response = self.client.post(
            get_dir_listing_url(None), {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: ['folder-%d' % f1.id],
        })
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)

    def test_message_error_user_no_site_on_move_for_site_admins(self):
        self._make_user_site_admin()
        response, url = self.request_move_root_folder()
        assert "You are not allowed to move some of the files and folders you selected." in\
            response.cookies['messages'].value, "Expected error message not found."
        assert response.status_code == 302

    def test_message_error_user_no_site_on_move(self):
        response, url = self.request_move_root_folder()
        assert response.status_code == 403, "Permission denied should be raised for no user"

    def request_move_root_folder(self):
        site = Site.objects.get(id=1)
        foo_root = Folder.objects.create(name='foo_root')
        foo = Folder.objects.create(name='foo', parent=foo_root)
        bar = Folder.objects.create(name='bar', site=site)
        return move_action(self.client, foo_root, bar, [foo])

    def test_move_to_clipboard_from_site_folders_for_site_admins(self):
        self._make_user_site_admin()
        self_cls = TestFolderTypePermissionLayerForRegularUser
        super(self_cls, self).test_move_to_clipboard_from_site_folders()

    def test_move_to_clipboard_from_site_folders(self):
        foo = Folder.objects.create(name='foo', site=Site.objects.get(id=1))
        file_foo = File.objects.create(
            original_filename='foo', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        self.assertEqual(
            self._get_clipboard_files().count(), 0)

        move_to_clipboard_action(self.client, None, [foo])
        self.assertEqual(
            self._get_clipboard_files().count(), 0)

        file_bar = File.objects.create(
            original_filename='bar', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        move_to_clipboard_action(self.client, foo, [file_bar])
        self.assertEqual(
            self._get_clipboard_files().count(), 1)

        file_baz = File.objects.create(
            original_filename='baz', folder=foo,
            file=dj_files.base.ContentFile('some data'))
        move_single_file_to_clipboard_action(
            self.client, foo, [file_baz])
        self.assertEqual(
            self._get_clipboard_files().count(), 2)

    def test_error_unallowed_restriction_change(self):
        self._make_user_site_admin()
        site = Site.objects.get(id=1)
        foo_root = Folder.objects.create(name='foo_root')
        unfiled_file = File.objects.create(name='unfiled_file', folder=foo_root)
        response, url = enable_restriction(
            self.client, foo_root, [unfiled_file], follow=False)
        assert "You are not allowed to modify the restrictions on the selected "\
            "files and folders." in response.cookies['messages'].value,\
            "Operation was expected to fail."


class TestSiteFolderRoleFiltering(TestCase, HelpersMixin):
    """
    Tests filer objects site filtering for following:
        * files/folders search
        * files/folders displayed in dir-listing view
        * destination folder filtering on move/copy actions
    """
    def setUp(self):
        self._create_simple_setup()
        filer_perms = Permission.objects.filter(
            content_type__app_label='filer')
        for gr in Group.objects.filter(
                id__in=Role.objects.values_list('group', flat=True)):
            gr.permissions.add(*filer_perms)
        restricted_groups = Group.objects.filter(
            id__in=Role.objects.filter(
                name__in=['editor', 'writer']
            ).values_list('group', flat=True)
        )
        for gr in restricted_groups:
            gr.permissions.remove(*list(Permission.objects.filter(
                content_type__app_label='filer',
                codename='can_restrict_operations')))

        for user in User.objects.all():
            user.set_password('secret')
            user.save()
        self.foo_site = Site.objects.get(name='foo.site.com')
        self.bar_site = Site.objects.get(name='bar.site.com')
        self.folders, self.files = self._build_folder_structure()

    def get_listed_objects(self, folder, data={}):
        response = self.client.get(get_dir_listing_url(folder), data)
        try:
            items = response.context['paginator'].object_list
        except:
            items = []
        return response, items

    def _build_folder_structure(self):
        unfiled_file = File.objects.create(original_filename='unfiled_file',
            file=dj_files.base.ContentFile('some data'))
        foo = Folder.objects.create(name='foo', site=self.foo_site)
        foo_file = File.objects.create(original_filename='foo_file',
            file=dj_files.base.ContentFile('some data'), folder=foo)
        bar = Folder.objects.create(name='bar', site=self.bar_site)
        bar_file = File.objects.create(original_filename='bar_file',
            file=dj_files.base.ContentFile('some data'), folder=bar)
        none = Folder.objects.create(name='no_site')
        none_file = File.objects.create(original_filename='none_file',
            file=dj_files.base.ContentFile('some data'), folder=none)
        core = Folder.objects.create(
            name='core', folder_type=Folder.CORE_FOLDER)
        core_file = File.objects.create(original_filename='core_file',
            file=dj_files.base.ContentFile('some data'), folder=core)

        return {'foo': foo, 'bar': bar, 'none': none, 'core': core}, {
            'foo_file': foo_file,
            'bar_file': bar_file,
            'unfiled_file': unfiled_file,
            'core_file': core_file,
            'none_file': none_file}

    def test_search_for_site_admin(self):
        # jack is admin on bar site
        self.client.login(username='jack', password='secret')
        response, items = self.get_listed_objects(None, {'q': 'file'})
        expected = set([self.files['core_file'], self.files['none_file'],
                        self.files['bar_file'], self.files['unfiled_file']])
        assert expected <= set(items)
        assert self.files['foo_file'] not in items
        assert len(expected) <= items.length

    def test_search_for_other_users(self):
        # bob is writer on bar site
        self.client.login(username='bob', password='secret')
        response, items = self.get_listed_objects(None, {'q': 'file'})
        expected = set([self.files['core_file'],
                        self.files['bar_file'], self.files['unfiled_file']])
        assert expected <= set(items)
        assert self.files['foo_file'] not in items
        assert self.files['none_file'] not in items
        assert len(expected) <= items.length

    def test_search_for_multi_site_user(self):
        # joe is site admin for foo and bar
        self.client.login(username='joe', password='secret')
        response, items = self.get_listed_objects(None, {'q': 'file'})
        expected = set(self.files.values())
        assert expected <= set(items)
        assert len(expected) <= items.length

    def test_dir_listing_for_site_admin(self):
        # jack is admin on bar site
        self.client.login(username='jack', password='secret')

        response, items = self.get_listed_objects(None)
        expected = set([
            self.folders['core'], self.folders['bar'], self.folders['none']])
        assert expected <= set(items)
        assert self.folders['foo'] not in items
        assert len(expected) == items.length

        response, items = self.get_listed_objects('unfiled')
        assert items.length == 1
        assert self.files['unfiled_file'] in items

        response, items = self.get_listed_objects(self.folders['core'])
        assert items.length == 1
        assert self.files['core_file'] in items

        response, items = self.get_listed_objects(self.folders['foo'])
        assert response.status_code == 403

        response, items = self.get_listed_objects(self.folders['none'])
        assert items.length == 1
        assert self.files['none_file'] in items

    def test_dir_listing_for_other_users(self):
        # bob is writer on bar site
        self.client.login(username='bob', password='secret')

        response, items = self.get_listed_objects(None)
        expected = set([self.folders['core'], self.folders['bar']])
        assert expected <= set(items)
        assert self.folders['foo'] not in items
        assert self.folders['none'] not in items
        assert len(expected) == items.length

        response = self.client.get(get_dir_listing_url('unfiled'))
        items = response.context['paginator'].object_list
        assert items.length == 1
        assert self.files['unfiled_file'] in items

        response, items = self.get_listed_objects(self.folders['core'])
        assert items.length == 1
        assert self.files['core_file'] in items

        response, items = self.get_listed_objects(self.folders['foo'])
        assert response.status_code == 403

        response, items = self.get_listed_objects(self.folders['none'])
        assert response.status_code == 403

    def _fetch_destination_names(self, current_folder):
        url = reverse('admin:filer-destination_folders')
        tree_data = json.loads(
            self.client.get(
                url, {
                    'parent': None,
                    'current_folder': current_folder
                }, **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
            ).content)
        return sorted([el['title'] for el in tree_data])

    def test_destination_filtering_for_site_admin(self):
        # joe is site admin for foo and bar
        self.client.login(username='joe', password='secret')

        bar2 = Folder.objects.create(name='bar2', site=self.bar_site)
        expected = sorted(['bar', 'bar2', 'foo'])
        self.assertItemsEqual(expected, self._fetch_destination_names(bar2.pk))

    def test_destination_filtering_for_multi_site_user(self):
        # bob will be a site admin on foo and writer on bar
        admin_role = Role.objects.get(name='site admin')
        admin_role.grant_to_user(
            User.objects.get(username='bob'), self.foo_site)
        bar2 = Folder.objects.create(name='bar2', site=self.bar_site)
        self.client.login(username='bob', password='secret')
        expected = sorted(['bar', 'bar2', 'foo'])
        self.assertItemsEqual(expected, self._fetch_destination_names(bar2.pk))

    def test_destination_filtering_for_other_users(self):
        # bob is writer on bar site
        self.client.login(username='bob', password='secret')
        bar2 = Folder.objects.create(name='bar2', site=self.bar_site)
        expected = sorted(['bar', bar2.name])
        self.assertItemsEqual(expected, self._fetch_destination_names(bar2.pk))
        bar = Folder.objects.get(name='bar')
        bar.restricted = True
        bar.save()
        assert ['bar2'] == self._fetch_destination_names(bar2.pk)

    def test_on_site_change_filtering(self):
        # jack is site admin on bar site
        self.client.login(username='jack', password='secret')
        response = self.client.get(
            reverse('admin:filer_folder_change',
                args=(self.folders['bar'].pk, )))
        self.assertEqual(response.status_code, 200)
        form = response.context_data['adminform'].form
        assert set([self.bar_site]) == set(form.fields['site'].queryset)
        self.client.logout()
        # bob is writer on bar
        self.client.login(username='bob', password='secret')
        response = self.client.get(
            reverse('admin:filer_folder_change',
                args=(self.folders['bar'].pk, )))
        self.assertEqual(response.status_code, 403)
        self.client.logout()
        # make bob a site admin on foo
        admin_role = Role.objects.get(name='site admin')
        admin_role.grant_to_user(
            User.objects.get(username='bob'), self.foo_site)
        # bob still doesn't have access on bar folder
        self.client.login(username='bob', password='secret')
        response = self.client.get(
            reverse('admin:filer_folder_change',
                args=(self.folders['bar'].pk, )))
        self.assertEqual(response.status_code, 403)
        # bob should have access on foo folder
        response = self.client.get(
            reverse('admin:filer_folder_change',
                args=(self.folders['foo'].pk, )))
        self.assertEqual(response.status_code, 200)
        form = response.context_data['adminform'].form
        assert set([self.foo_site]) == set(form.fields['site'].queryset)
        self.client.logout()
        # joe is multi site admin
        self.client.login(username='joe', password='secret')
        response = self.client.get(
            reverse('admin:filer_folder_change',
                args=(self.folders['bar'].pk, )))
        self.assertEqual(response.status_code, 200)
        form = response.context_data['adminform'].form
        expected = set([self.bar_site, self.foo_site])
        assert expected == set(form.fields['site'].queryset)
        self.client.logout()


class TestFolderTypeFunctionality(TestCase):
    """
    Tests folder operations are done correctly:
        * folder owner is set by user from request
        * folder parent id is passed from admin view request to the add folder
            form
        * folder validation on save
        * folder type is kept from parent and changes are passed to
            descendants
    """
    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_superuser = user.is_staff = user.is_active = True
        user.save()
        self.client.login(username=username, password=password)
        self.user = user

    def test_on_site_delete_folder_is_not_deleted(self):
        s1 = Site.objects.create(name='bar', domain='bar.example.com')
        f1 = Folder.objects.create(name='foo', site=s1)
        s1.delete()
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)
        self.assertEqual(Folder.objects.get(id=f1.id).site, None)

    def test_on_owner_delete_folder_is_not_deleted(self):
        u1 = User.objects.create(username='bar')
        f1 = Folder.objects.create(name='foo', owner=u1)
        file1 = File.objects.create(name='some_file', owner=u1)
        u1.delete()
        self.assertEqual(Folder.objects.filter(id=f1.id).count(), 1)
        self.assertEqual(Folder.objects.get(id=f1.id).owner, None)
        self.assertEqual(File.objects.get(id=file1.id).owner, None)

    def test_owner_set_by_request_user_on_folder_form(self):
        response = self.client.post(
            get_make_root_folder_url(),
            {'name': 'foo', 'site': 1})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].owner, self.user)

    def test_make_folder_view_sets_parent_id_correctly(self):
        response = self.client.post(
            get_make_root_folder_url(),
            {'name': 'foo', 'site': 1, 'parent_id': ''})
        foo = Folder.objects.get(name='foo')
        self.assertEqual(foo.parent, None)
        response = self.client.post(
            get_make_root_folder_url(),
            {'name': 'bar', 'site': 1, 'parent_id': foo.id})
        bar = Folder.objects.get(name='bar')
        self.assertEqual(bar.parent_id, foo.id)

        response = self.client.post(
            reverse('admin:filer_folder_change', args=(bar.pk, )),
            {'post': ['yes'], 'name': 'baz'})
        self.assertEqual(response.status_code, 302)
        bar = Folder.objects.get(name='baz')
        self.assertEqual(bar.parent_id, foo.id)

    def test_folder_validation_works_on_model_and_form(self):
        foo = Folder(name='foo')
        foo.site_id = 1
        foo.save()

        bar = Folder(name='foo', site_id=1)
        with self.assertRaisesRegexp(ValidationError, 'name is already in use'):
            bar.full_clean()
        bar.name = 'bar'
        bar.site = None
        with self.assertRaisesRegexp(ValidationError, 'Site is required'):
            bar.full_clean()
        bar.site = Site.objects.get(id=1)
        bar.folder_type = Folder.CORE_FOLDER
        with self.assertRaisesRegexp(ValidationError, 'Site must be empty.'):
            bar.full_clean()

        response = self.client.post(
            get_make_root_folder_url(),
            {'name': 'bar'})
        self.assertIn('Site is required', response.content)

        response = self.client.post(
            get_make_root_folder_url(),
            {'name': 'foo'})
        self.assertIn('name is already in use', response.content)

    def test_folder_type_conversion_propagate_changes(self):
        site = Site.objects.get(id=1)
        foo = Folder.objects.create(name='foo', site=site)
        bar = Folder.objects.create(
            name='bar', site=site, parent=foo)
        foo.folder_type = Folder.CORE_FOLDER
        foo.save()
        foo = Folder.objects.get(name='foo')
        bar = Folder.objects.get(name='bar')
        self.assertEqual(foo.folder_type, Folder.CORE_FOLDER)
        self.assertEqual(foo.site, None)
        self.assertEqual(bar.folder_type, Folder.CORE_FOLDER)
        self.assertEqual(bar.site, None)
        foo.folder_type = Folder.SITE_FOLDER
        foo.site = site
        foo.save()
        foo = Folder.objects.get(name='foo')
        bar = Folder.objects.get(name='bar')
        self.assertEqual(foo.folder_type, Folder.SITE_FOLDER)
        self.assertEqual(foo.site, site)
        self.assertEqual(bar.folder_type, Folder.SITE_FOLDER)
        self.assertEqual(bar.site, site)


class TestValidationOnFileName(TestCase):
    """
    Test if validation errors are thrown when user tries to enter an invalid
        file name.
    """

    def _make_file_for_each_type(self):
        return [
            Archive.objects.create(
                original_filename='zippy.zip',
                file=dj_files.base.ContentFile('zippy')),
            Image.objects.create(
                original_filename='image.jpg',
                file=dj_files.base.ContentFile('image')),
            File.objects.create(
                original_filename='file.txt',
                file=dj_files.base.ContentFile('file'))]

    def test_name_with_slash(self):
        files = self._make_file_for_each_type()
        for a_file in files:
            a_file.full_clean()
            a_file.name = "some/name"
            with self.assertRaisesRegexp(
                    ValidationError, 'Slashes are not allowed'):
                a_file.full_clean()

    def test_name_without_extension(self):
        files = self._make_file_for_each_type()
        for a_file in files:
            a_file.full_clean()
            a_file.name = "some_name"
            with self.assertRaisesRegexp(
                    ValidationError, 'without extension is not allowed'):
                a_file.full_clean()

    def test_name_extension_change(self):
        zip_file, image_file, plain_file = self._make_file_for_each_type()
        err_msg1 = 'preserve.*extensions'
        err_msg2 = 'Extension.*not allowed'

        # should work for valid extensions
        zip_file.name = 'abc.zip'
        zip_file.full_clean()

        # should allow image extensions change(ex.: from .png to .jpg)
        for valid_ext in Image._filename_extensions:
            image_file.name = 'abc%s' % valid_ext
            image_file.full_clean()

        # should allow extension changes that "imply" filer objects conversion
        for ext in ['.txt', '.png', '.jpeg', '.tiff']:
            with self.assertRaisesRegexp(ValidationError, err_msg1):
                zip_file.name = 'abc%s' % ext
                zip_file.full_clean()

        for ext in ['.txt', '.zip', '.tiff']:
            with self.assertRaisesRegexp(ValidationError, err_msg1):
                image_file.name = 'abc%s' % ext
                image_file.full_clean()

        for ext in Image._filename_extensions + Archive._filename_extensions:
            with self.assertRaisesRegexp(ValidationError, err_msg2):
                plain_file.name = 'abc%s' % ext
                plain_file.full_clean()


class TestRestrictionFunctionality(TestCase):
    """
    Tests that restriction is applied correctly
        * folder restricted => all descendants are restricted
        * file restricted => keeps restriction from parent
            even if set to unrestricted
    """

    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_superuser = user.is_staff = user.is_active = True
        user.save()
        self.client.login(username=username, password=password)
        self.user = user

    def test_make_folder_restricted(self):
        foo = Folder.objects.create(name='foo')
        bar = Folder.objects.create(name='bar', parent=foo)
        foo_file = File.objects.create(
            original_filename='foo_file', folder=foo)
        bar_file = File.objects.create(
            original_filename='bar_file', folder=bar)
        assert File.objects.filter(restricted=True).count() == 0
        assert Folder.objects.filter(restricted=True).count() == 0

        foo.restricted = True
        foo.save()

        assert File.objects.filter(restricted=False).count() == 0
        assert Folder.objects.filter(restricted=False).count() == 0

    def test_cascade_change_on_parent_restriction(self):
        s1 = Site.objects.get(id=1)
        foo = Folder.objects.create(name='foo', site=s1)
        foo_file = File.objects.create(
            original_filename='foo_file', folder=foo)
        bar = Folder.objects.create(name='bar', parent=foo)
        bar_file = File.objects.create(
            original_filename='bar_file', folder=bar)
        baz = Folder.objects.create(name='baz', parent=bar)
        bar.restricted = True
        bar.save()
        self.assertEqual(Folder.objects.get(id=foo.id).restricted, False)
        self.assertEqual(File.objects.get(id=foo_file.id).restricted, False)
        self.assertEqual(Folder.objects.get(id=bar.id).restricted, True)
        self.assertEqual(File.objects.get(id=bar_file.id).restricted, True)
        self.assertEqual(Folder.objects.get(id=baz.id).restricted, True)
        self.assertEqual(Folder.objects.filter(site=s1).count(), 3)
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(foo.pk, )), {
                'name': 'foo_only_name_changed', 'post': ['yes'],
                'restricted': False,
                'site': s1.id,
            })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Folder.objects.get(id=foo.id).restricted, False)
        self.assertEqual(File.objects.get(id=foo_file.id).restricted, False)
        self.assertEqual(Folder.objects.get(id=bar.id).restricted, True)
        self.assertEqual(File.objects.get(id=bar_file.id).restricted, True)
        self.assertEqual(Folder.objects.get(id=baz.id).restricted, True)
        response = self.client.post(
            reverse('admin:filer_folder_change', args=(foo.pk, )), {
                'name': 'foo', 'post': ['yes'],
                'restricted': True,
                'site': s1.id,
            })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Folder.objects.filter(restricted=True).count(), 3)
        self.assertEqual(File.objects.filter(restricted=True).count(), 2)

    def test_make_file_restricted(self):
        foo = Folder.objects.create(name='foo', restricted=True)
        foo_file = File.objects.create(
            original_filename='foo_file', folder=foo)
        assert foo_file.restricted == True

        foo_file.restricted = False
        foo_file.save()

        assert File.objects.get(pk=foo_file.pk).restricted == True
        assert Folder.objects.get(pk=foo.pk).restricted == True


class TestFrozenAssetsPermissions(TestCase):
    """
    Tests folder operations on frozen assets are restricted:
        * add/move/copy/delete/extract in/from restricted folder
    """

    def _user_setup(self, user):
        foo_base_group = Group.objects.create(name='foo_base_group')
        developer_role = Role.objects.create(
            name='foo_role', group=foo_base_group,
            is_site_wide=True)
        developer_role.grant_to_user(user, self.site)

    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_staff = user.is_active = True
        user.save()
        filer_perms = Permission.objects.filter(
            content_type__app_label='filer').exclude(
            codename='can_restrict_operations')
        user.user_permissions = filer_perms
        self.site = Site.objects.get(id=1)
        self._user_setup(user)
        self.client.login(username=username, password=password)
        self.user = user
        # create file storage image
        self.img = create_image()
        self.image_name = 'foo_file.jpg'
        self.filename = os.path.join(
            os.path.dirname(__file__), self.image_name)
        self.img.save(self.filename, 'JPEG')
        # build filer files structure
        self.folders, self.files = self._build_folder_structure()

    def _build_folder_structure(self):
        foo = Folder.objects.create(
            name='foo', site=self.site, restricted=True)
        file_obj= DjangoFile(open(self.filename), name=self.image_name)
        foo_file = Image.objects.create(original_filename=self.image_name,
            file=file_obj, folder=foo)
        foo_zippy = Archive.objects.create(original_filename='foo_file.zip',
            file=dj_files.base.ContentFile('zippy'), folder=foo)
        assert foo.restricted == foo_file.restricted
        return {'foo': foo}, {'foo_file': foo_file, 'foo_zippy': foo_zippy}

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)

    def test_make_subfolder_in_restricted(self):
        post_data = {
            "name": 'subfolder', "_popup": 1,
            'parent_id': self.folders['foo'].id}
        response = self.client.post(get_make_root_folder_url(), post_data)
        self.assertEqual(response.status_code, 403)

    def test_move_from_clipboard_in_restricted(self):
        bar_file = File.objects.create(
            original_filename='bar_file',
            file=dj_files.base.ContentFile('some data'))
        clipboard, _ = Clipboard.objects.get_or_create(user=self.user)
        clipboard.append_file(bar_file)
        response = paste_clipboard_to_folder(
            self.client, self.folders['foo'], clipboard)
        self.assertEqual(response.status_code, 403)

    def test_move_from_restricted_to_clipboard(self):
        clipboard, _ = Clipboard.objects.get_or_create(user=self.user)
        self.assertEqual(clipboard.files.count(), 0)
        self.assertEqual(clipboard.clipboarditem_set.count(), 0)

        response, url = move_to_clipboard_action(
            self.client, self.folders['foo'], [self.files['foo_file']])

        clipboard, _ = Clipboard.objects.get_or_create(user=self.user)
        self.assertEqual(clipboard.files.count(), 0)
        self.assertEqual(clipboard.clipboarditem_set.count(), 0)
        self.assertEqual(
            File.objects.filter(folder=self.folders['foo']).count(), 2)

        response = move_single_file_to_clipboard_action(
            self.client, self.folders['foo'], [self.files['foo_file']])

        clipboard, _ = Clipboard.objects.get_or_create(user=self.user)
        self.assertEqual(clipboard.files.count(), 0)
        self.assertEqual(clipboard.clipboarditem_set.count(), 0)
        self.assertEqual(
            File.objects.filter(folder=self.folders['foo']).count(), 2)

    def test_move_restricted_to_clipboard(self):
        bar = Folder.objects.create(
            name='bar', site=self.site)
        bar_file = File.objects.create(
            original_filename='bar_file', restricted=True,
            file=dj_files.base.ContentFile('some data'), folder=bar)
        response = move_single_file_to_clipboard_action(
            self.client, bar, [bar_file])
        self.assertEqual(response.status_code, 403)

    def test_move_in_restricted(self):
        bar = Folder.objects.create(name='bar', site=self.site)
        bar_subfolder = Folder.objects.create(
            name='bar1', site=self.site, parent=bar)
        bar_file = File.objects.create(
            original_filename='bar_file',
            file=dj_files.base.ContentFile('some data'), folder=bar)
        response, _ = move_action(
            self.client, bar, self.folders['foo'], [bar_file])
        self.assert_invalid_move_destination_response(response)

        response, _ = move_action(
            self.client, bar, self.folders['foo'], [bar_subfolder])
        assert Folder.objects.filter(parent=self.folders['foo']).count() == 0
        bar_file.folder = None
        bar_file.save()
        response, _ = move_action(
            self.client, 'unfiled', self.folders['foo'], [bar_file])
        assert File.objects.filter(folder=self.folders['foo']).count() == 2


    def assert_invalid_move_destination_response(self, response):
        assert "The destination was not valid so the selected files and folders were "\
            "not moved. Please try again." in response.cookies['messages'].value,\
            "Was expecting error message because the destination is invalid"
        assert response.status_code == 302

    def test_move_restricted_in_dest(self):
        bar = Folder.objects.create(name='bar', site=self.site)
        foo_subfolder = Folder.objects.create(
            name='foo_subfolder', site=self.site)
        foo_subfolder.parent = self.folders['foo']
        foo_subfolder.save()
        response, _ = move_action(
            self.client, self.folders['foo'], bar, [foo_subfolder])
        self.assertEqual(File.objects.filter(folder=bar).count(), 0)

        response, _ = move_action(
            self.client, self.folders['foo'], bar, [self.files['foo_file']])
        self.assertEqual(File.objects.filter(folder=bar).count(), 0)

    def test_extract_in_restricted(self):
        self.assertEqual(
            File.objects.filter(folder=self.folders['foo']).count(), 2)
        url = get_dir_listing_url(self.folders['foo'])
        response = self.client.post(url, {
            'action': 'extract_files',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(self.files['foo_zippy'])]})
        self.assertEqual(
            File.objects.filter(folder=self.folders['foo']).count(), 2)

    def test_delete_from_restricted(self):
        self.assertEqual(
            File.objects.filter(id=self.files['foo_file'].id).count(), 1)

        url = get_dir_listing_url(self.folders['foo'])
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(self.files['foo_file'])],
        })
        self.assertEqual(
            File.objects.filter(id=self.files['foo_file'].id).count(), 1)

        url = get_dir_listing_url(None)
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(self.folders['foo'])],
        })
        self.assertEqual(
            File.objects.filter(id=self.files['foo_file'].id).count(), 1)
        self.assertEqual(
            Folder.objects.filter(id=self.folders['foo'].id).count(), 1)

    def test_delete_restricted(self):
        bar = Folder.objects.create(name='bar', site=self.site)
        bar_file = File.objects.create(
            original_filename='bar_file', restricted=True,
            file=dj_files.base.ContentFile('some data'), folder=bar)

        url = get_dir_listing_url(bar)
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(bar_file)],
        })
        self.assertEqual(response.status_code, 403)

    def test_copy_from_restricted(self):
        bar = Folder.objects.create(name='bar', site=self.site)
        url = get_dir_listing_url(self.folders['foo'])
        response = self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'destination': bar.id,
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(self.files['foo_file'])]})

        assert File.objects.filter(folder=bar).count() == 1
        assert File.objects.get(folder=bar).restricted == False

    def test_copy_in_restricted(self):
        bar = Folder.objects.create(name='bar', site=self.site)
        bar_file = File.objects.create(
            original_filename='bar_file',
            file=dj_files.base.ContentFile('some data'), folder=bar)

        url = get_dir_listing_url(bar)
        response = self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'destination': self.folders['foo'].id,
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(bar_file)]})
        self.assert_invalid_copy_destination_response(response)

        url = get_dir_listing_url(None)
        response = self.client.post(url, {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'destination': self.folders['foo'].id,
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(bar)]})
        self.assert_invalid_copy_destination_response(response)

    def assert_invalid_copy_destination_response(self, response):
        assert "The selected destination was not valid, so the selected files and "\
            "folders were not copied. Please try again." in response.cookies['messages'].value,\
            "Was expecting error message because the destination is invalid"
        assert response.status_code == 302


class TestSharedSitePermissions(TestCase):
    """
    Tests actions on shared folders
    """
    def _user_setup(self, user):
        filer_perms = Permission.objects.filter(
            content_type__app_label='filer')
        foo_base_group = Group.objects.create(name='foo_base_group')
        foo_base_group.permissions.add(*filer_perms)
        some_role = Role.objects.create(
            name='foo_role', group=foo_base_group,
            is_site_wide=True)
        some_role.grant_to_user(user, self.site)

    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_staff = user.is_active = True
        user.save()
        self.site = Site.objects.get(id=1)
        self.other_site = Site.objects.create(
            domain='bar@example.com', name='BAR')
        self._user_setup(user)
        self.client.login(username=username, password=password)
        self.user = user
        self._create_folder_structure()

    def _create_folder_structure(self):
        self.foo = Folder.objects.create(name='foo', site=self.site)
        self.foo_child = Folder.objects.create(name='foo_child',
            parent=self.foo)
        self.bar = Folder.objects.create(name='bar', site=self.other_site)
        self.bar_child = Folder.objects.create(name='bar_child',
            parent=self.bar)
        self.bar.shared.add(self.site)
        assert self.foo_child.site.id == self.foo.site.id
        assert self.bar_child.site.id == self.bar.site.id

    def get_listed_objects(self, folder, data={}):
        response = self.client.get(get_dir_listing_url(folder), data)
        try:
            items = response.context['paginator'].object_list
        except:
            items = []
        return response, items

    def test_view_shared_folder(self):
        bar_file = File.objects.create(
            original_filename='bar_file.txt', folder=self.bar,
            file=dj_files.base.ContentFile('file'))
        resp, items = self.get_listed_objects(None)
        self.assertEqual(set([self.foo, self.bar]), set(items))
        resp, items = self.get_listed_objects(self.bar)
        self.assertEqual(set([bar_file, self.bar_child]), set(items))
        bar_file.folder = self.bar_child
        bar_file.save()
        resp, items = self.get_listed_objects(self.bar_child)
        self.assertEqual(set([bar_file]), set(items))

    def test_add_in_shared_folder(self):
        response = self.client.post(
            get_make_root_folder_url(),
            {'name': 'foo', 'parent_id': self.bar.id})
        self.assertEqual(response.status_code, 403)

    def test_change_shared_folder(self):
        response = self.client.get(
            reverse('admin:filer_folder_change', args=(self.bar.pk, )))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(
            reverse('admin:filer_folder_change', args=(self.bar_child.pk, )))
        self.assertEqual(response.status_code, 403)

    def test_delete_shared_folder(self):
        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(self.bar.pk, )),
            {'post': 'yes'})
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            reverse('admin:filer_folder_delete', args=(self.bar_child.pk, )),
            {'post': 'yes'})
        self.assertEqual(response.status_code, 403)

        url = get_dir_listing_url(None)
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: filer_obj_as_checkox(self.bar),
        })
        self.assertEqual(Folder.objects.filter(id=self.bar.id).count(), 1)
        self.assertEqual(
            Folder.objects.filter(id=self.bar_child.id).count(), 1)

        url = get_dir_listing_url(self.bar)
        response = self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: filer_obj_as_checkox(self.bar_child),
        })
        self.assertEqual(Folder.objects.filter(id=self.bar.id).count(), 1)
        self.assertEqual(
            Folder.objects.filter(id=self.bar_child.id).count(), 1)

    def test_move_from_shared_folder(self):
        baz = Folder.objects.create(name='baz', site=self.other_site)
        response, _ = move_action(
            self.client, self.bar, baz, [self.bar_child])
        self.assertEqual(Folder.objects.get(
            id=self.bar_child.id).parent.id, self.bar.id)

    def test_move_to_shared_folder(self):
        unfiled_file = File.objects.create(
            original_filename='bar_file.txt',
            file=dj_files.base.ContentFile('file'))
        response, _ = move_action(
            self.client, 'unfiled', self.bar, [unfiled_file])
        self.assertEqual(File.objects.get(id=unfiled_file.id).folder, None)
        response, _ = move_action(
            self.client, 'unfiled', self.bar_child, [unfiled_file])
        self.assertEqual(File.objects.get(id=unfiled_file.id).folder, None)

    def test_extract_files_shared_folder(self):
        bar_zippy = Archive.objects.create(
            original_filename='bar_zippy.zip', folder=self.bar,
            file=dj_files.base.ContentFile('zippy'))
        assert Folder.objects.get(id=self.bar.id).files.count() == 1
        url = get_dir_listing_url(self.bar)
        response = self.client.post(url, {
            'action': 'extract_files',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(bar_zippy)]})
        assert Folder.objects.get(id=self.bar.id).files.count() == 1

    def test_move_to_clipboard_from_shared_folder(self):
        bar_file = File.objects.create(
            original_filename='bar_file.txt', folder=self.bar,
            file=dj_files.base.ContentFile('file'))
        response = move_to_clipboard_action(
            self.client, self.bar, [bar_file])
        self.assertEqual(Clipboard.objects.all().get().files.count(), 0)
        move_single_file_to_clipboard_action(
            self.client, self.bar, [bar_file])
        self.assertEqual(Clipboard.objects.all().get().files.count(), 0)


class TestSharedFolderFunctionality(TestCase):
    """
       * only root folders can be shared
       * shared sites changes are propagated for all descendants
    """
    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_superuser = user.is_staff = user.is_active = True
        user.save()
        self.client.login(username=username, password=password)
        self.user = user

    def test_changes_are_propagated_to_all_descendants(self):
        site = Site.objects.get(id=1)
        foo = Folder.objects.create(name='foo')
        bar = Folder.objects.create(name='bar', parent=foo)
        baz = Folder.objects.create(name='baz', parent=bar)
        foo.shared.add(site)
        for folder in Folder.objects.all():
            self.assertListEqual(list(folder.shared.all().order_by('domain')),
                                 list(foo.shared.all().order_by('domain')))

    def test_subfolder_inherits_from_parent(self):
        s1 = Site.objects.create(name='foo', domain='foo.example.com')
        data_to_post = {
             "name": 'new_root',
             "site": 1,
             "shared": [1, s1.id],
        }
        response = self.client.post(get_make_root_folder_url(), data_to_post)
        root = Folder.objects.get(name='new_root')
        self.assertListEqual(list(root.shared.all().order_by('domain')),
                             list(Site.objects.all().order_by('domain')))
        data_to_post = {
             "name": 'child',
             "parent_id": root.id
        }
        response = self.client.post(get_make_root_folder_url(), data_to_post)
        child = Folder.objects.get(name='child')
        self.assertListEqual(list(child.shared.all().order_by('domain')),
                             list(root.shared.all().order_by('domain')))
        data_to_post = {
             "name": 'child2',
             "parent_id": child.id
        }
        response = self.client.post(get_make_root_folder_url(), data_to_post)
        child2 = Folder.objects.get(name='child2')
        self.assertListEqual(list(child2.shared.all().order_by('domain')),
                             list(child.shared.all().order_by('domain')))

    def test_only_root_folders_can_be_shared(self):
        foo = Folder.objects.create(name='foo')
        bar = Folder.objects.create(name='bar', parent=foo)
        response = self.client.get(
            reverse('admin:filer_folder_change', args=(foo.pk, )))
        self.assertEqual(response.status_code, 200)
        self.assertIn('adminform', response.context_data)
        form = response.context_data['adminform'].form
        self.assertItemsEqual(
            sorted(['name', 'restricted', 'shared', 'site']),
            sorted(form.fields.keys()))

        response = self.client.get(
            reverse('admin:filer_folder_change', args=(bar.pk, )))
        self.assertEqual(response.status_code, 200)
        self.assertIn('adminform', response.context_data)
        form = response.context_data['adminform'].form
        self.assertItemsEqual(
            sorted(['name', 'restricted']), sorted(form.fields.keys()))

    def test_shared_sites_are_inherited_on_move(self):
        s1 = Site.objects.create(name='s1', domain='s1.example.com')
        s2 = Site.objects.create(name='s2', domain='s2.example.com')
        site = Site.objects.get(id=1)
        foo = Folder.objects.create(name='foo', site=site)
        foo_1 = Folder.objects.create(name='foo1', parent=foo)
        bar = Folder.objects.create(name='bar', site=site)
        bar_1 = Folder.objects.create(name='bar1', parent=bar)
        bar_12 = Folder.objects.create(name='bar12', parent=bar_1)
        foo.shared.add(s1)
        bar.shared.add(s2)
        response, _ = move_action(self.client, bar, foo, [bar_1])
        foo_descendants = Folder.objects.get(
            name='foo').get_descendants()
        for desc_folder in [bar_1, bar_12]:
            self.assertIn(desc_folder, foo_descendants)
            self.assertItemsEqual(desc_folder.shared.all(), [s1])

    def test_shared_sites_are_inherited_on_copy(self):
        s1 = Site.objects.create(name='s1', domain='s1.example.com')
        s2 = Site.objects.create(name='s2', domain='s2.example.com')
        site = Site.objects.get(id=1)
        foo = Folder.objects.create(name='foo', site=site)
        foo_1 = Folder.objects.create(name='foo1', parent=foo)
        bar = Folder.objects.create(name='bar', site=site)
        bar_1 = Folder.objects.create(name='bar1', parent=bar)
        bar_12 = Folder.objects.create(name='bar12', parent=bar_1)
        foo.shared.add(s1)
        bar.shared.add(s2)

        response = self.client.post(get_dir_listing_url(bar), {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'suffix': '',
            'destination': foo.id,
            helpers.ACTION_CHECKBOX_NAME: filer_obj_as_checkox(bar_1),
        }, follow=True)

        bar_descendants = Folder.objects.get(
            name='bar').get_descendants()
        for desc_folder in [bar_1, bar_12]:
            self.assertIn(desc_folder, bar_descendants)
            self.assertItemsEqual(desc_folder.shared.all(), [s2])

        bar_1_copy = Folder.objects.get(name='bar1', parent=foo)
        bar_12_copy = Folder.objects.get(name='bar12', parent=bar_1_copy)
        foo_descendants = Folder.objects.get(
            name='foo').get_descendants(include_self=True)
        for desc_folder in [bar_1_copy, bar_12_copy, foo_1, foo]:
            self.assertIn(desc_folder, foo_descendants)
            self.assertItemsEqual(desc_folder.shared.all(), [s1])
        foo.shared.remove(s1)
        for desc_folder in [bar_1_copy, bar_12_copy, foo_1, foo]:
            self.assertIn(desc_folder, foo_descendants)
            self.assertItemsEqual(desc_folder.shared.all(), [])


class TestAdminTools(TestCase):
    """
    Tests for cases that are not covered by the tests above
    """
    def _user_setup(self, user):
        filer_perms = Permission.objects.filter(
            content_type__app_label='filer').exclude(
            codename='can_restrict_operations')
        foo_base_group = Group.objects.create(name='foo_base_group')
        foo_base_group.permissions.add(*filer_perms)
        some_role = Role.objects.create(
            name='foo_role', group=foo_base_group,
            is_site_wide=True)
        some_role.grant_to_user(user, self.site)

    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_staff = user.is_active = True
        user.save()
        self.site = Site.objects.get(id=1)
        self.other_site = Site.objects.create(
            domain='bar@example.com', name='BAR')
        self._user_setup(user)
        self.client.login(username=username, password=password)
        self.user = user

    def test_valid_destination(self):
        request = HttpRequest()
        request.user = self.user
        from filer.admin.tools import is_valid_destination

        foo = Folder.objects.create(name='foo')
        # no site
        self.assertEqual(is_valid_destination(request, foo), False)
        foo.site = self.site
        foo.save()
        self.assertEqual(is_valid_destination(request, foo), True)
        # restricted
        foo.restricted = True
        foo.save()
        self.assertEqual(is_valid_destination(request, foo), False)
        # core folder
        foo.folder_type = Folder.CORE_FOLDER
        foo.restricted = False
        foo.save()
        self.assertEqual(is_valid_destination(request, foo), False)
        # other site's folder
        bar = Folder.objects.create(name='bar', site=self.other_site)
        self.assertEqual(is_valid_destination(request, bar), False)
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual(is_valid_destination(request, bar), True)

    def test_current_site_filtering(self):
        request = HttpRequest()
        request.GET = {}
        request.GET['current_site'] = '1'
        request.user = self.user
        from filer.admin.tools import _filter_available_sites, files_available
        self.assertItemsEqual([1L], _filter_available_sites('1', request.user))
        request.GET['current_site'] = 1
        self.assertItemsEqual([1L], _filter_available_sites('1', request.user))
        request.GET['current_site'] = 1L
        self.assertItemsEqual([1L], _filter_available_sites('1', request.user))
        request.GET['current_site'] = '2'
        self.assertEqual([], _filter_available_sites('2', request.user))
        f1 = File.objects.create(original_filename='foo_file')
        request.GET['current_site'] = '1'
        self.assertEqual(
            len(files_available('1', request.user, File.objects.filter(id=f1.id))), 0)

    def test_multi_files_perms_for_restricted_descendants(self):
        f1 = Folder.objects.create(name='1')
        f2 = Folder.objects.create(name='2', parent=f1)
        file2 = File.objects.create(original_filename='21', folder=f2)
        f3 = Folder.objects.create(name='3', parent=f2)
        file3 = File.objects.create(original_filename='31', folder=f3)
        f1.site = self.other_site
        f1.save()

        request = HttpRequest()
        request.user = self.user
        from filer.admin.tools import has_multi_file_action_permission
        # test for folders from other site
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f1.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f2.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f3.id)), False)
        f1.site = self.site
        f1.save()
        # root folder and user is not site admin
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f1.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f2.id)), True)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f3.id)), True)
        # level 1 file restriction
        file2.restricted = True
        file2.save()
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f1.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f2.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f3.id)), True)
        # level 1 folder restriction
        file2.restricted = False
        file2.save()
        f2.restricted = True
        f2.save()
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f1.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f2.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f3.id)), False)
        # level 2 folder restriction
        f2.restricted = False
        f2.save()
        f3.restricted = True
        f3.save()
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f1.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f2.id)), False)
        self.assertEqual(has_multi_file_action_permission(
            request, File.objects.none(),
            Folder.objects.filter(id=f3.id)), False)
        f1.restricted = True
        f1.save()
        self.assertEqual(File.objects.filter(restricted=False).count(), 0)
        self.assertEqual(Folder.objects.filter(restricted=False).count(), 0)


class TestMPTTCorruptionsOnFolderOperations(TestCase):

    def setUp(self):
        self.site = Site.objects.get(id=1)
        self.src_folder = Folder.objects.create(name='1', site=self.site)
        self.dst_folder = Folder.objects.create(name='2', site=self.site)
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_superuser = user.is_staff = user.is_active = True
        user.save()
        self.client.login(username=username, password=password)
        self.user = user
        self.dirs, self.files = [], []

    def test_move_operation(self):
        create_folder_structure(
            depth=2, sibling=2,
            parent=Folder.objects.get(id=self.src_folder.id))
        # making sure no corruptions exist
        TreeChecker().find_corruptions()
        to_move = Folder.objects.filter(
            parent__pk=self.src_folder.pk)
        move_action(self.client, self.src_folder, self.dst_folder, to_move)
        TreeChecker().find_corruptions()

    def test_copy_operation(self):
        create_folder_structure(
            depth=2, sibling=2,
            parent=Folder.objects.get(id=self.src_folder.id))
        TreeChecker().find_corruptions()
        to_copy = [
            filer_obj_as_checkox(child)
            for child in Folder.objects.filter(
                parent__pk=self.src_folder.pk)]
        self.client.post(get_dir_listing_url(self.src_folder), {
            'action': 'copy_files_and_folders',
            'post': 'yes',
            'suffix': '',
            'destination': self.dst_folder.id,
            helpers.ACTION_CHECKBOX_NAME: to_copy,
        })
        TreeChecker().find_corruptions()

    def test_multi_folders_delete_operation(self):
        create_folder_structure(
            depth=2, sibling=2,
            parent=Folder.objects.get(id=self.src_folder.id))
        TreeChecker().find_corruptions()
        to_delete = [
            filer_obj_as_checkox(child)
            for child in Folder.objects.filter(
                parent__pk=self.src_folder.pk)]
        response = self.client.post(get_dir_listing_url(self.src_folder), {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: to_delete,
        })
        TreeChecker().find_corruptions()

    def test_single_folder_delete_operation(self):
        child_src_folder = Folder.objects.create(
            name='1', parent=self.src_folder)
        create_folder_structure(
            depth=2, sibling=2,
            parent=Folder.objects.get(id=child_src_folder.id))
        TreeChecker().find_corruptions()
        delete_url = reverse(
            'admin:filer_folder_delete', args=(child_src_folder.pk, ))
        response = self.client.post(delete_url, {'post': ['yes']})
        TreeChecker().find_corruptions()

    def tearDown(self):
        for file_path in self.files:
            os.remove(file_path)
        for path in self.dirs:
            os.removedirs(path)

    def test_extract_zip(self):
        parent_path = os.path.dirname(__file__)
        self.dirs = ['1/1', '1/2', '2/1']
        self.dirs = [os.path.join(parent_path, d) for d in self.dirs]
        self.files = []
        for path in self.dirs:
            os.makedirs(path)
            file_path = os.path.join(path, 'name.txt')
            with open(file_path, 'w') as fp:
                fp.write('some data')
            self.files.append(file_path)

        zip_file_path = os.path.join(parent_path, 'zip_file.zip')
        zip_file = zipfile.ZipFile(zip_file_path, 'w')
        for f in self.files:
            arc_filename = f.replace(parent_path, '')[1:]
            zip_file.write(f, arc_filename)
        zip_file.close()
        self.files.append(zip_file_path)

        filer_zipfile = Archive.objects.create(
            original_filename='zip_file.zip', folder=self.src_folder,
            file=dj_files.File(open(zip_file_path), name='zip_file.zip'),
        )
        self.client.post(get_dir_listing_url(self.src_folder), {
            'action': 'extract_files',
            helpers.ACTION_CHECKBOX_NAME:
                [filer_obj_as_checkox(filer_zipfile)]})
        TreeChecker().find_corruptions()


class TestImageChangeForm(TestCase):

    def setUp(self):
        self.user = create_superuser()
        self.client.login(username='admin', password='secret')

    def tearDown(self):
        self.client.logout()
        for f in File.all_objects.all():
            f.delete(to_trash=False)

    def create_filer_image(self, image_name, **kwargs):
        image = create_image()
        image_path = os.path.join(os.path.dirname(__file__), image_name)
        image.save(image_path, 'JPEG')
        file_obj = DjangoFile(open(image_path), name=image_name)
        kwargs.update({'original_filename': image_name, 'file': file_obj})
        image = Image.objects.create(**kwargs)
        os.remove(image_path)
        return image

    def _create_another_PIL_image(self):
        import PIL
        size = (100, 50)
        im = PIL.Image.new('RGB', size)
        draw = PIL.ImageDraw.Draw(im)
        red = (255, 0, 0)
        text_pos = (10, 10)
        text = "Hello World!"
        draw.text(text_pos, text, fill=red)
        del draw
        return im

    def test_image_change_name_and_data(self):
        with SettingsOverride(filer_settings,
                              FILER_PUBLICMEDIA_UPLOAD_TO=by_path,
                              FOLDER_AFFECTS_URL=True):
            foo = Folder.objects.create(name='foo')
            orig_img = self.create_filer_image(
                'one.jpg', folder=foo, owner=self.user)
            sha1_before = orig_img.sha1
            self.assertEqual(orig_img.file.name,
                             'foo/{}_one.jpg'.format(sha1_before[:10]))

            another_img_name = 'new_one.jpg'
            another_img_path = os.path.join(os.path.dirname(__file__),
                                            another_img_name)
            pil_img = self._create_another_PIL_image()
            pil_img.save(another_img_path, 'JPEG')
            from django.core.files.uploadedfile import SimpleUploadedFile
            with open(another_img_path, 'rb') as new_img:
                img_url = reverse('admin:filer_image_change',
                                  args=(orig_img.pk, ))
                response = self.client.post(img_url, {
                    'name': another_img_name,
                    'file': SimpleUploadedFile(new_img.name, new_img.read())
                })
                orig_img = File.objects.get(id=orig_img.id)
                self.assertEqual(orig_img.file.name,
                                 'foo/{}_new_one.jpg'.format(orig_img.sha1[:10]))
                self.assertNotEqual(sha1_before, orig_img.sha1)
            os.remove(another_img_path)

    def test_image_change_name_only(self):
        with SettingsOverride(filer_settings,
                              FILER_PUBLICMEDIA_UPLOAD_TO=by_path,
                              FOLDER_AFFECTS_URL=True):
            foo = Folder.objects.create(name='foo')
            orig_img = self.create_filer_image(
                'two.jpg', folder=foo, owner=self.user)
            img_url = reverse('admin:filer_image_change',
                              args=(orig_img.pk, ))
            response = self.client.post(img_url, {
                'name': 'new_two.jpg',
                '_save': '',
            })
            folder_url = reverse(
                'admin:filer-directory_listing', kwargs={'folder_id': foo.id})
            self.assertRedirects(response, folder_url)
            orig_img = File.objects.get(id=orig_img.id)
            self.assertEqual(orig_img.file.name,
                             'foo/{}_new_two.jpg'.format(orig_img.sha1[:10]))

    def test_image_change_data_only(self):
        with SettingsOverride(filer_settings,
                              FILER_PUBLICMEDIA_UPLOAD_TO=by_path,
                              FOLDER_AFFECTS_URL=True):
            foo = Folder.objects.create(name='foo')
            orig_img = self.create_filer_image(
                'three.jpg', folder=foo, owner=self.user)
            sha1_before = orig_img.sha1
            another_img_name = 'new_three.jpg'
            another_img_path = os.path.join(os.path.dirname(__file__),
                                            another_img_name)
            pil_img = self._create_another_PIL_image()
            pil_img.save(another_img_path, 'JPEG')
            from django.core.files.uploadedfile import SimpleUploadedFile
            with open(another_img_path, 'rb') as new_img:
                img_url = reverse('admin:filer_image_change',
                                  args=(orig_img.pk, ))
                response = self.client.post(img_url, {
                    'file': SimpleUploadedFile(new_img.name, new_img.read())
                })
                orig_img = File.objects.get(id=orig_img.id)
                self.assertNotEqual(sha1_before, orig_img.sha1)
            os.remove(another_img_path)

    def test_image_change_name_in_popup(self):
        """
        Use case: open a popup, save image changes and then select the image
        """
        with SettingsOverride(filer_settings,
                              FILER_PUBLICMEDIA_UPLOAD_TO=by_path,
                              FOLDER_AFFECTS_URL=True):
            foo = Folder.objects.create(name='foo')
            orig_img = self.create_filer_image(
                'four.jpg', folder=foo, owner=self.user)
            img_url = reverse('admin:filer_image_change', args=(orig_img.pk, ))
            response = self.client.post(img_url, {
                'name': 'new_four.jpg',
                '_save': '', '_popup': '1',
            })
            folder_url = "{}{}".format(
                reverse('admin:filer-directory_listing', kwargs={'folder_id': foo.id}),
                "?_popup=1")
            self.assertRedirects(response, folder_url)
            orig_img = File.objects.get(id=orig_img.id)
            self.assertEqual(orig_img.file.name,
                             'foo/{}_new_four.jpg'.format(orig_img.sha1[:10]))


class TrashAdminTests(TestCase):

    def setUp(self):
        self.user = create_superuser()
        self.client.login(username='admin', password='secret')

    def tearDown(self):
        self.client.logout()
        for f in File.all_objects.all():
            f.delete(to_trash=False)

    def create_filer_image(self, image_name, **kwargs):
        image = create_image()
        image_path = os.path.join(os.path.dirname(__file__), image_name)
        image.save(image_path, 'JPEG')
        file_obj = DjangoFile(open(image_path), name=image_name)
        kwargs.update({
            'original_filename': image_name,
            'file': file_obj
            })
        image = Image.objects.create(**kwargs)
        os.remove(image_path)
        return image

    def test_restore_item_view(self):
        img_dir = Folder.objects.create(name='dir')
        img_dir_child = Folder.objects.create(
            name='img_dir_child', parent=img_dir)
        img = self.create_filer_image('to_be_deleted.jpg', folder=img_dir)
        img_child = self.create_filer_image(
            'child_to_be_deleted.jpg', folder=img_dir_child)
        Image.objects.get(id=img.id).delete()
        Image.objects.get(id=img_child.id).delete()
        Folder.objects.get(id=img_dir.id).delete()

        # search for child file
        response = self.client.get(reverse('admin:filer_trash_changelist'), {
            'q': 'child_to_be_deleted'})
        items_displayed = response.context['paginator'].object_list
        self.assertEqual(len(items_displayed), 1)
        self.assertEqual(items_displayed[0].id, img_child.id)

        root_restore_url = reverse(
            'admin:filer_trash_item', args=('folder', img_dir.id,))
        for filer_model, filer_obj_id in [('file', img_child.id), (
                                          'folder', img_dir_child.id)]:
            restorable_item_url = reverse('admin:filer_trash_item',
                                          args=(filer_model, filer_obj_id,))
            response = self.client.get(restorable_item_url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(
                response.get('location').endswith(root_restore_url))
            restore_item_url = reverse('admin:filer_restore_items',
                                       args=(filer_model, filer_obj_id,))
            response = self.client.post(restore_item_url, {'post': 'yes'})
            self.assertEqual(response.status_code, 403)


def get_listed_objects(client, folder, data={}):
    response = client.get(get_dir_listing_url(folder), data)
    try:
        items = response.context['paginator'].object_list
    except:
        items = []
    return response, items


class TestImageFiltering(TestCase):

    def setUp(self):
        username = 'login_using_foo'
        password = 'secret'
        user = User.objects.create_user(username=username, password=password)
        user.is_staff = user.is_superuser = user.is_active = True
        user.save()
        self.client.login(username=username, password=password)
        self.user = user
        # create file storage image
        self.img = create_image()
        self.image_name = 'foo_file.jpg'
        self.filename = os.path.join(
            os.path.dirname(__file__), self.image_name)
        self.img.save(self.filename, 'JPEG')
        self.site = Site.objects.first()
        self.foo = Folder.objects.create(
            name='foo', site=self.site, restricted=True)
        file_obj= DjangoFile(open(self.filename), name=self.image_name)
        self.foo_image = Image.objects.create(original_filename=self.image_name,
                                              file=file_obj, folder=self.foo)
        self.foo_file = File.objects.create(original_filename=self.image_name,
                                            file=file_obj, folder=self.foo)

    def test_get_images(self):
        self.client.login(username='jack', password='secret')
        _, items = get_listed_objects(self.client, self.foo, {'file_type': 'image'})
        assert {self.foo_image} == set(items)
        _, items = get_listed_objects(self.client, self.foo)
        assert {self.foo_image, self.foo_file} == set(items)
