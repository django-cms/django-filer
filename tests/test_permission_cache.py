from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase

from filer import settings as filer_settings
from filer.cache import (
    clear_folder_permission_cache,
    get_folder_perm_cache_key,
    get_folder_permission_cache,
    update_folder_permission_cache,
)
from filer.models import Folder, FolderPermission
from tests.helpers import SettingsOverride


User = get_user_model()


class PermissionCacheTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.permission = 'can_read'
        self.id_list = {1, 5, 8}

    def tearDown(self):
        clear_folder_permission_cache(self.user)

    def test_get_folder_perm_cache_key_generates_unique_key_for_user_and_permission(self):
        key = get_folder_perm_cache_key(self.user, self.permission)
        self.assertEqual(key, f"filer:perm:{self.permission}")

    def test_get_folder_permission_cache_returns_permissions_for_existing_cache(self):
        cache.set(get_folder_perm_cache_key(self.user, self.permission), {self.user.pk: self.id_list})
        permissions = get_folder_permission_cache(self.user, self.permission)
        self.assertEqual(permissions, self.id_list)

    def test_get_folder_permission_cache_returns_none_for_non_existing_cache(self):
        permissions = get_folder_permission_cache(self.user, self.permission)
        self.assertIsNone(permissions)

    def test_empty_cache_group_grant(self):
        group = Group.objects.create(name='readers')
        folder = Folder.objects.create(name='shared')
        FolderPermission.objects.create(
            group=group, folder=folder, type=FolderPermission.THIS,
            can_read=FolderPermission.ALLOW,
        )
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), set())
            self.user.groups.add(group)
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), {folder.pk})

    def test_empty_cache_direct_grant(self):
        folder = Folder.objects.create(name='shared')
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), set())
            FolderPermission.objects.create(
                user=self.user, folder=folder, type=FolderPermission.THIS,
                can_read=FolderPermission.ALLOW,
            )
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), {folder.pk})

    def test_empty_cache_public_grant(self):
        folder = Folder.objects.create(name='shared')
        grant = FolderPermission.objects.create(
            everybody=True, folder=folder, type=FolderPermission.THIS, can_read=None,
        )
        with SettingsOverride(filer_settings, FILER_ENABLE_PERMISSIONS=True):
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), set())
            # Bulk updates bypass model signals and admin cache invalidation.
            FolderPermission.objects.filter(pk=grant.pk).update(can_read=FolderPermission.ALLOW)
            self.assertEqual(FolderPermission.objects.get_read_id_list(self.user), {folder.pk})

    def test_clear_folder_permission_cache_clears_all_permissions_for_user(self):
        cache.set(get_folder_perm_cache_key(self.user, 'can_read'), {self.user.pk: ['can_read']})
        cache.set(get_folder_perm_cache_key(self.user, 'can_edit'), {self.user.pk: ['can_edit']})
        clear_folder_permission_cache(self.user)
        self.assertIsNone(cache.get(get_folder_perm_cache_key(self.user, 'can_read')))
        self.assertIsNone(cache.get(get_folder_perm_cache_key(self.user, 'can_edit')))

    def test_clear_folder_permission_cache_clears_specific_permission_for_user(self):
        cache.set(get_folder_perm_cache_key(self.user, self.permission), {self.user.pk: self.id_list})
        clear_folder_permission_cache(self.user, self.permission)
        self.assertIsNone(cache.get(get_folder_perm_cache_key(self.user, self.permission)))

    def test_update_folder_permission_cache_updates_permissions_for_user_and_permission(self):
        update_folder_permission_cache(self.user, self.permission, self.id_list)
        permissions = get_folder_permission_cache(self.user, self.permission)
        self.assertEqual(permissions, self.id_list)

    def test_update_folder_permission_cache_overwrites_existing_cache_value(self):
        update_folder_permission_cache(self.user, self.permission, {2})
        update_folder_permission_cache(self.user, self.permission, self.id_list)
        permissions = get_folder_permission_cache(self.user, self.permission)
        self.assertEqual(permissions, self.id_list)
