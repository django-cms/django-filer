#-*- coding: utf-8 -*-
from django.contrib.auth.models import User, Group
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase
from filer import settings as filer_settings
from filer.models.clipboardmodels import Clipboard
from filer.models.foldermodels import Folder, FolderPermission
from filer.models.imagemodels import Image
from filer.tests.utils import Mock
from filer.tests.helpers import create_image, create_superuser
import os

class FolderPermissionsTestCase(TestCase):

    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

        self.unauth_user = User.objects.create(username='unauth_user')

        self.owner = User.objects.create(username='owner')

        self.test_user1 = User.objects.create(username='test1', password='secret')
        self.test_user2 = User.objects.create(username='test2', password='secret')

        self.group1 = Group.objects.create(name='name1')
        self.group2 = Group.objects.create(name='name2')

        self.test_user1.groups.add(self.group1)
        self.test_user2.groups.add(self.group2)

        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename), name=self.image_name)
        # This is actually a "file" for filer considerations
        self.image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=self.file)
        self.clipboard = Clipboard.objects.create(user=self.superuser)
        self.clipboard.append_file(self.image)

        self.folder = Folder.objects.create(name='test_folder')

        self.folder_perm = Folder.objects.create(name='test_folder2')

    def tearDown(self):
        self.image.delete()

    def test_superuser_has_rights(self):
        request = Mock()
        setattr(request, 'user', self.superuser)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_unlogged_user_has_no_rights(self):
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True
            request = Mock()
            setattr(request, 'user', self.unauth_user)

            result = self.folder.has_read_permission(request)
            self.assertEqual(result, False)
        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_unlogged_user_has_rights_when_permissions_disabled(self):
        request = Mock()
        setattr(request, 'user', self.unauth_user)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_owner_user_has_rights(self):
        # Set owner as the owner of the folder.
        self.folder.owner = self.owner
        request = Mock()
        setattr(request, 'user', self.owner)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_groups(self):
        request1 = Mock()
        setattr(request1, 'user', self.test_user1)
        request2 = Mock()
        setattr(request2, 'user', self.test_user2)

        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.has_read_permission(request1), False)
            self.assertEqual(self.folder.has_read_permission(request2), False)
            self.assertEqual(self.folder_perm.has_read_permission(request1), False)
            self.assertEqual(self.folder_perm.has_read_permission(request2), False)

            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.ALL, group=self.group1, can_edit=True, can_read=True, can_add_children=True)
            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.ALL, group=self.group2, can_edit=True, can_read=True, can_add_children=True)

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_read_permission(request2), False)
            self.assertEqual(self.folder_perm.has_read_permission(request1), False)
            self.assertEqual(self.folder_perm.has_read_permission(request2), True)

            self.test_user1.groups.add(self.group2)
            self.test_user2.groups.add(self.group1)

            self.assertEqual(self.folder.has_read_permission(request1), True)
            self.assertEqual(self.folder.has_read_permission(request2), True)
            self.assertEqual(self.folder_perm.has_read_permission(request1), True)
            self.assertEqual(self.folder_perm.has_read_permission(request2), True)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
