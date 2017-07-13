#-*- coding: utf-8 -*-
from __future__ import absolute_import

import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase

from .. import settings as filer_settings
from ..models.clipboardmodels import Clipboard
from ..models.foldermodels import Folder, FolderPermission
from ..settings import FILER_IMAGE_MODEL
from ..utils.loader import load_model
from .helpers import create_image, create_superuser
from .utils import Mock

Image = load_model(FILER_IMAGE_MODEL)


class FolderPermissionsTestCase(TestCase):

    def setUp(self):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
        except ImportError:
            from django.contrib.auth.models import User  # NOQA
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
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename, 'rb'), name=self.image_name)
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
        result = self.folder.user_can_view(self.superuser)
        self.assertEqual(result, True)

    def test_unlogged_user_has_no_rights(self):
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True
            result = self.folder.user_can_view(self.unauth_user)
            self.assertEqual(result, False)
        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_unlogged_user_has_rights_when_permissions_disabled(self):
        result = self.folder.user_can_view(self.unauth_user)
        self.assertEqual(result, True)

    def test_owner_user_has_rights(self):
        # Set owner as the owner of the folder.
        self.folder.owner = self.owner
        result = self.folder.user_can_view(self.owner)
        self.assertEqual(result, True)

    def test_combined_groups(self):
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.user_can_view(self.test_user1), False)
            self.assertEqual(self.folder.user_can_view(self.test_user2), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user1), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)
            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.folder.user_can_view(self.test_user1), True)
            self.assertEqual(self.folder.user_can_view(self.test_user2), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user1), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), True)

            self.test_user1.groups.add(self.group2)
            self.test_user2.groups.add(self.group1)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.folder.user_can_view(self.test_user1), True)
            self.assertEqual(self.folder.user_can_view(self.test_user2), True)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user1), True)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), True)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_overlapped_groups_deny1(self):
        # Tests overlapped groups with explicit deny
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.user_can_view(self.test_user1), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user1), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)
            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.test_user1.groups.filter(pk=self.group1.pk).exists(), True)
            self.assertEqual(self.test_user1.groups.filter(pk=self.group2.pk).exists(), False)

            self.assertEqual(self.folder.user_can_view(self.test_user1), True)
            self.assertEqual(self.folder.user_can_change(self.test_user1), False)

            self.assertEqual(self.test_user1.groups.count(), 1)

            self.test_user1.groups.add(self.group2)

            self.assertEqual(self.test_user1.groups.count(), 2)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.folder.user_can_view(self.test_user1), True)
            self.assertEqual(self.folder.user_can_change(self.test_user1), False)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_overlapped_groups_deny2(self):
        # Tests overlapped groups with explicit deny
        # Similar test to test_overlapped_groups_deny1, only order of groups is different
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.user_can_view(self.test_user2), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.DENY, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.DENY)
            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # We have to invalidate cache
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.test_user2.groups.filter(pk=self.group2.pk).exists(), True)
            self.assertEqual(self.test_user2.groups.filter(pk=self.group1.pk).exists(), False)

            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), True)
            self.assertEqual(self.folder_perm.user_can_change(self.test_user2), False)

            self.assertEqual(self.test_user2.groups.count(), 1)

            self.test_user2.groups.add(self.group1)

            self.assertEqual(self.test_user2.groups.count(), 2)

            # We have to invalidate cache
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), True)
            self.assertEqual(self.folder_perm.user_can_change(self.test_user2), False)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_overlapped_groups1(self):
        # Tests overlapped groups without explicit deny
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.user_can_view(self.test_user1), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user1), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group1, can_edit=None, can_read=FolderPermission.ALLOW, can_add_children=None)
            FolderPermission.objects.create(folder=self.folder, type=FolderPermission.CHILDREN, group=self.group2, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.test_user1.groups.filter(pk=self.group1.pk).exists(), True)
            self.assertEqual(self.test_user1.groups.filter(pk=self.group2.pk).exists(), False)

            self.assertEqual(self.folder.user_can_view(self.test_user1), True)
            self.assertEqual(self.folder.user_can_change(self.test_user1), False)

            self.assertEqual(self.test_user1.groups.count(), 1)

            self.test_user1.groups.add(self.group2)

            self.assertEqual(self.test_user1.groups.count(), 2)

            # We have to invalidate cache
            delattr(self.folder, 'permission_cache')

            self.assertEqual(self.folder.user_can_view(self.test_user1), True)
            self.assertEqual(self.folder.user_can_view(self.test_user1), True)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting

    def test_overlapped_groups2(self):
        # Tests overlapped groups without explicit deny
        # Similar test to test_overlapped_groups1, only order of groups is different
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        try:
            filer_settings.FILER_ENABLE_PERMISSIONS = True

            self.assertEqual(self.folder.user_can_view(self.test_user2), False)
            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), False)

            self.assertEqual(FolderPermission.objects.count(), 0)

            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group2, can_edit=None, can_read=FolderPermission.ALLOW, can_add_children=None)
            FolderPermission.objects.create(folder=self.folder_perm, type=FolderPermission.CHILDREN, group=self.group1, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)

            self.assertEqual(FolderPermission.objects.count(), 2)

            # We have to invalidate cache
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.test_user2.groups.filter(pk=self.group2.pk).exists(), True)
            self.assertEqual(self.test_user2.groups.filter(pk=self.group1.pk).exists(), False)

            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), True)
            self.assertEqual(self.folder_perm.user_can_change(self.test_user2), False)

            self.assertEqual(self.test_user2.groups.count(), 1)

            self.test_user2.groups.add(self.group1)

            self.assertEqual(self.test_user2.groups.count(), 2)

            # We have to invalidate cache
            delattr(self.folder_perm, 'permission_cache')

            self.assertEqual(self.folder_perm.user_can_view(self.test_user2), True)
            self.assertEqual(self.folder_perm.user_can_change(self.test_user2), True)

        finally:
            filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
