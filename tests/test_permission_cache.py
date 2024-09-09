from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from filer.cache import get_folder_perm_cache_key, get_folder_permission_cache, clear_folder_permission_cache, update_folder_permission_cache


User = get_user_model()


class PermissionCacheTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.permission = 'can_read'
        self.id_list = [1, 5, 8]

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
