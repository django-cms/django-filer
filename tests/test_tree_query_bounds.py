from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from filer import settings as filer_settings
from filer.admin.tools import (
    check_files_edit_permissions,
    check_folder_edit_permissions,
    check_folder_read_permissions,
)
from filer.cache import clear_folder_permission_cache
from filer.models import File, Folder, FolderPermission
from tests.helpers import create_superuser


SMALL_WIDTH = 2
LARGE_WIDTH = 16


def build_tree(name, width):
    # A root with `width` children, each with one grandchild.
    root = Folder.objects.create(name=name)
    expected = set()
    for index in range(width):
        child = Folder.objects.create(name=f'{name} child {index}', parent=root)
        grandchild = Folder.objects.create(name=f'{name} grandchild {index}', parent=child)
        expected.update((child.pk, grandchild.pk))
    return root, expected


def count_queries(func):
    with CaptureQueriesContext(connection) as queries:
        result = func()
    return result, len(queries)


class DescendantIdsTests(TestCase):
    def test_descendant_queries_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root, expected = build_tree(f'tree {width}', width)
            descendants, counts[width] = count_queries(root.get_descendants_ids)

            self.assertIsInstance(descendants, list)
            self.assertEqual(len(descendants), len(expected))
            self.assertEqual(set(descendants), expected)

        # Width must not add queries; only depth may.
        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])

    def test_leaf_has_no_descendants(self):
        leaf = Folder.objects.create(name='leaf')
        self.assertEqual(leaf.get_descendants_ids(), [])


class LimitedSearchQueryTests(TestCase):
    def setUp(self):
        create_superuser()
        self.client.login(username='admin', password='secret')

    def search(self, folder):
        url = reverse('admin:filer-directory_listing', args=(folder.pk,))
        return self.client.get(url, {'q': 'match', 'limit_search_to_folder': 'on'})

    def test_limited_search_queries_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root, expected = build_tree(f'tree {width}', width)
            deepest = Folder.objects.filter(pk__in=expected, children__isnull=True).first()
            match = File.objects.create(original_filename=f'match {width}.txt', folder=deepest)
            File.objects.create(original_filename=f'match outside {width}.txt')
            self.search(root)

            response, counts[width] = count_queries(lambda: self.search(root))

            files = [item for item in response.context['paginated_items'].object_list if isinstance(item, File)]
            self.assertEqual([file_obj.pk for file_obj in files], [match.pk])

        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])


class TreePermissionCheckTests(TestCase):
    def setUp(self):
        permissions = patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True)
        permissions.start()
        self.addCleanup(permissions.stop)

        self.owner = get_user_model().objects.create(username='owner')
        self.user = get_user_model().objects.create(username='editor', is_staff=True)
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=('change_folder', 'change_file'),
        ))
        clear_folder_permission_cache(self.user)
        self.addCleanup(clear_folder_permission_cache, self.user)

    def build(self, name, width, owner=None):
        root, expected = build_tree(name, width)
        Folder.objects.filter(pk__in=expected | {root.pk}).update(owner=owner)
        leaves = Folder.objects.filter(pk__in=expected, children__isnull=True)
        File.objects.bulk_create([
            File(original_filename=f'{leaf.name}.txt', folder=leaf, owner=self.owner)
            for leaf in leaves
        ])
        return Folder.objects.get(pk=root.pk), leaves

    def grant(self, folder, scope, **grants):
        FolderPermission.objects.create(user=self.user, folder=folder, type=scope, **grants)

    def request(self):
        # A fresh user object starts with empty Django permission caches.
        request = RequestFactory().post('/')
        request.user = get_user_model().objects.get(pk=self.user.pk)
        clear_folder_permission_cache(request.user)
        return request

    def assert_allowed(self, check, root):
        check(self.request(), [root])

    def assert_denied(self, check, root):
        with self.assertRaises(PermissionDenied):
            check(self.request(), [root])

    def test_subtree_grants_allow(self):
        root, _ = self.build('tree', SMALL_WIDTH)
        self.grant(root, FolderPermission.CHILDREN, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW)

        self.assert_allowed(check_folder_edit_permissions, root)
        self.assert_allowed(check_folder_read_permissions, root)

    def test_deep_folder_denial(self):
        root, leaves = self.build('tree', SMALL_WIDTH)
        self.grant(root, FolderPermission.CHILDREN, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW)
        self.grant(leaves.last(), FolderPermission.THIS, can_edit=FolderPermission.DENY)

        self.assert_denied(check_folder_edit_permissions, root)
        self.assert_allowed(check_folder_read_permissions, root)

    def test_deep_file_needs_permission(self):
        root, _ = self.build('tree', SMALL_WIDTH)
        empty_root, _ = build_tree('empty', SMALL_WIDTH)
        for folder in (root, empty_root):
            self.grant(folder, FolderPermission.CHILDREN, can_edit=FolderPermission.ALLOW)
        self.user.user_permissions.remove(Permission.objects.get(codename='change_file'))

        # Only the files on the deepest level lack permission.
        self.assert_denied(check_folder_edit_permissions, root)
        self.assert_allowed(check_folder_edit_permissions, empty_root)

    def test_owned_folders_bypass_grants(self):
        root, leaves = self.build('tree', SMALL_WIDTH, owner=self.user)

        self.assert_allowed(check_folder_edit_permissions, root)
        self.assert_allowed(check_folder_read_permissions, root)

        Folder.objects.filter(pk=leaves.last().pk).update(owner=self.owner)
        self.assert_denied(check_folder_edit_permissions, root)
        self.assert_denied(check_folder_read_permissions, root)

    def test_owned_files_bypass_grants(self):
        folder = Folder.objects.create(name='ungranted')
        owned = File.objects.create(original_filename='owned.txt', folder=folder, owner=self.user)
        other = File.objects.create(original_filename='other.txt', folder=folder, owner=self.owner)

        check_files_edit_permissions(self.request(), [owned])
        with self.assertRaises(PermissionDenied):
            check_files_edit_permissions(self.request(), [other])

    def test_check_queries_follow_depth(self):
        for check in (check_folder_edit_permissions, check_folder_read_permissions):
            counts = {}
            for width in (SMALL_WIDTH, LARGE_WIDTH):
                root, _ = self.build(f'{check.__name__} {width}', width)
                self.grant(root, FolderPermission.CHILDREN, can_edit=FolderPermission.ALLOW, can_read=FolderPermission.ALLOW)
                request = self.request()
                _, counts[width] = count_queries(lambda: check(request, [root]))

            with self.subTest(check=check.__name__):
                self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])
