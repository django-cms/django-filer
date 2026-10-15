import io
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from filer import settings as filer_settings
from filer.admin.patched.admin_utils import NestedObjects
from filer.admin.tools import (
    check_files_edit_permissions,
    check_folder_edit_permissions,
    check_folder_read_permissions,
    filter_in_batches,
    load_subtrees,
)
from filer.cache import clear_folder_permission_cache
from filer.models import Clipboard, File, Folder, FolderPermission
from filer.settings import FILER_IMAGE_MODEL
from filer.utils.loader import load_model
from tests.helpers import create_image, create_superuser


Image = load_model(FILER_IMAGE_MODEL)


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


class MessageStub:
    # Admin actions report through messages; tests only need them accepted.
    def add(self, *args, **kwargs):
        pass


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

    def test_descendants_keep_tree_order(self):
        # Names sort opposite to creation order, so key order cannot pass.
        root = Folder.objects.create(name='root')
        b = Folder.objects.create(name='b', parent=root)
        b_child = Folder.objects.create(name='b child', parent=b)
        a = Folder.objects.create(name='a', parent=root)
        a_z = Folder.objects.create(name='z', parent=a)
        a_y = Folder.objects.create(name='y', parent=a)

        # Name-ordered and depth first, as the recursive version returned them.
        self.assertEqual(root.get_descendants_ids(), [a.pk, a_y.pk, a_z.pk, b.pk, b_child.pk])

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

    def test_ownerless_items_need_grants(self):
        # An unsaved user has no key; that must not match a missing owner.
        request = RequestFactory().post('/')
        request.user = get_user_model()(username='unsaved', is_staff=True)
        folder = Folder.objects.create(name='ownerless')
        file_obj = File.objects.create(original_filename='ownerless.txt')

        # Isolate the owner check: grant lookups find nothing.
        no_grants = {f'get_{name}_id_list': lambda user: set() for name in ('read', 'edit', 'add_children')}
        with patch.multiple(FolderPermission.objects, **no_grants):
            for item in (folder, file_obj):
                for permission in ('read', 'edit', 'add_children'):
                    with self.subTest(item=type(item).__name__, permission=permission):
                        self.assertFalse(item.has_generic_permission(request, permission))

    def test_owned_images_bypass_grants(self):
        folder = Folder.objects.create(name='ungranted images')
        buffer = io.BytesIO()
        create_image().save(buffer, 'JPEG')
        images = [
            Image.objects.create(
                original_filename=f'{owner.username}.jpg', folder=folder, owner=owner, mime_type='image/jpeg',
                file=ContentFile(buffer.getvalue(), name=f'{owner.username}.jpg'),
            )
            for owner in (self.user, self.owner)
        ]

        check_files_edit_permissions(self.request(), images[:1])
        with self.assertRaises(PermissionDenied):
            check_files_edit_permissions(self.request(), images[1:])

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


class DeleteActionTests(TestCase):
    def setUp(self):
        create_superuser()
        self.client.login(username='admin', password='secret')

    def delete(self, folder):
        url = reverse('admin:filer-directory_listing-root')
        return self.client.post(url, {
            'action': 'delete_files_or_folders',
            'post': 'yes',
            helpers.ACTION_CHECKBOX_NAME: [f'folder-{folder.pk}'],
        })

    def test_delete_queries_follow_depth(self):
        # Warm the content type cache used by deletion logging.
        self.delete(build_tree('warmup', SMALL_WIDTH)[0])
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root, descendants = build_tree(f'tree {width}', width)
            _, counts[width] = count_queries(lambda: self.delete(root))

            self.assertFalse(Folder.objects.filter(pk__in=descendants | {root.pk}).exists())

        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])

    def test_confirmation_shows_paths(self):
        parent = Folder.objects.create(name='parent')
        root, _ = build_tree('shown', SMALL_WIDTH)
        Folder.objects.filter(pk=root.pk).update(parent=parent)
        response = self.client.post(reverse('admin:filer-directory_listing', args=(parent.pk,)), {
            'action': 'delete_files_or_folders',
            helpers.ACTION_CHECKBOX_NAME: [f'folder-{root.pk}'],
        })

        for index in range(SMALL_WIDTH):
            self.assertContains(response, f'/parent/shown/shown child {index}/shown grandchild {index}</a>')
        self.assertTrue(Folder.objects.filter(pk=root.pk).exists())


class DestinationFolderTests(TestCase):
    def setUp(self):
        permissions = patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True)
        permissions.start()
        self.addCleanup(permissions.stop)

        self.user = get_user_model().objects.create(username='mover', is_staff=True)
        self.user.user_permissions.add(Permission.objects.get(codename='change_folder'))
        clear_folder_permission_cache(self.user)
        self.addCleanup(clear_folder_permission_cache, self.user)
        self.folder_admin = admin.site._registry[Folder]

    def destinations(self, selected, current, allow_self):
        request = RequestFactory().post('/')
        request.user = get_user_model().objects.get(pk=self.user.pk)
        clear_folder_permission_cache(request.user)
        return self.folder_admin._list_all_destination_folders(
            request, Folder.objects.filter(pk__in=[folder.pk for folder in selected]), current, allow_self,
        )

    def grant(self, folder, **grants):
        FolderPermission.objects.create(user=self.user, folder=folder, type=FolderPermission.CHILDREN, **grants)

    def test_destination_choices(self):
        a = Folder.objects.create(name='A')
        a1 = Folder.objects.create(name='A1', parent=a)
        a1a = Folder.objects.create(name='A1a', parent=a1)
        a2 = Folder.objects.create(name='A2', parent=a)
        a2a = Folder.objects.create(name='A2a', parent=a2)
        b = Folder.objects.create(name='B')
        Folder.objects.create(name='B1', parent=b)
        self.grant(a, can_read=FolderPermission.ALLOW)
        self.grant(a1, can_add_children=FolderPermission.ALLOW)

        indent = '&nbsp;&nbsp;'
        cases = (
            # Selected folders and their subtrees are excluded; B is unreadable.
            (False, [
                (a, ('/A', False)),
                (a1, (f'{indent}/A/A1', False)),
                (a1a, (f'{indent * 2}/A/A1/A1a', True)),
            ]),
            (True, [
                (a, ('/A', False)),
                (a1, (f'{indent}/A/A1', True)),
                (a1a, (f'{indent * 2}/A/A1/A1a', True)),
                (a2, (f'{indent}/A/A2', False)),
                (a2a, (f'{indent * 2}/A/A2/A2a', False)),
            ]),
        )
        for allow_self, expected in cases:
            with self.subTest(allow_self=allow_self):
                actual = self.destinations([a2], a1, allow_self)
                self.assertEqual(
                    [(folder.pk, (str(label), enabled)) for folder, (label, enabled) in actual],
                    [(folder.pk, choice) for folder, choice in expected],
                )

    def test_destination_queries_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root, expected = build_tree(f'tree {width}', width)
            self.grant(root, can_read=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW)
            destinations, counts[width] = count_queries(lambda: self.destinations([], None, False))

            self.assertLessEqual(expected, {folder.pk for folder, _ in destinations})

        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])


class ActionTreeTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.folder_admin = admin.site._registry[Folder]

    def build(self, name, width):
        # Files sit on both tree levels; the parent gives labels an ancestor.
        parent = Folder.objects.create(name=f'{name} parent')
        root, _ = build_tree(name, width)
        Folder.objects.filter(pk=root.pk).update(parent=parent)
        for folder in Folder.objects.filter(name__startswith=f'{name} ').exclude(pk=parent.pk):
            # Toggling visibility moves stored files, so each needs content.
            content = ContentFile(b'data', name=f'{folder.name}.txt')
            File.objects.create(original_filename=content.name, file=content, folder=folder, is_public=False)
        return Folder.objects.get(pk=root.pk)

    def request(self):
        request = RequestFactory().post('/')
        request.user = self.superuser
        request._messages = MessageStub()
        return request

    def label(self, obj):
        # Reload so expected labels never reuse instances from the code under test.
        fresh = type(obj).objects.get(pk=obj.pk)
        return self.folder_admin._format_callback(fresh, self.superuser, admin.site, set())

    def expected_tree(self, folder):
        nested = []
        for child in Folder.objects.filter(parent=folder).order_by('name'):
            nested.append(self.label(child))
            subtree = self.expected_tree(child)
            if subtree:
                nested.append(subtree)
        nested.extend(self.label(file_obj) for file_obj in sorted(folder.files))
        return nested

    def move_listing(self, root):
        return self.folder_admin._list_all_to_copy_or_move(
            self.request(), File.objects.none(), Folder.objects.filter(pk=root.pk),
        )

    def test_move_listing_matches_tree(self):
        root = self.build('listed', SMALL_WIDTH)
        self.assertEqual(self.move_listing(root), [self.label(root), self.expected_tree(root)])

    def test_move_listing_queries_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root = self.build(f'tree {width}', width)
            _, counts[width] = count_queries(lambda: self.move_listing(root))
        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])

    def add_images(self, root):
        buffer = io.BytesIO()
        create_image().save(buffer, 'JPEG')
        for leaf in Folder.objects.filter(parent__parent=root):
            content = ContentFile(buffer.getvalue(), name=f'{leaf.name}.jpg')
            Image.objects.create(original_filename=content.name, file=content, folder=leaf, mime_type='image/jpeg')

    def expected_resize(self, folder):
        nested = []
        for child in Folder.objects.filter(parent=folder).order_by('name'):
            subtree = self.expected_resize(child)
            if subtree:
                nested.extend((self.label(child), subtree))
        nested.extend(self.label(file_obj) for file_obj in sorted(folder.files) if isinstance(file_obj, Image))
        return nested

    def resize_listing(self, root):
        return self.folder_admin._list_all_to_resize(
            self.request(), File.objects.none(), Folder.objects.filter(pk=root.pk),
        )

    def test_resize_listing_matches_tree(self):
        root = self.build('resized', SMALL_WIDTH)
        self.add_images(root)
        expected = self.expected_resize(root)
        self.assertTrue(expected)
        self.assertEqual(self.resize_listing(root), [self.label(root), expected])

    def test_resize_listing_queries_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root = self.build(f'resize {width}', width)
            self.add_images(root)
            _, counts[width] = count_queries(lambda: self.resize_listing(root))
        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])

    def folder_reads(self, func):
        with CaptureQueriesContext(connection) as queries:
            func()
        return sum(query['sql'].startswith('SELECT') and 'FROM "filer_folder"' in query['sql'] for query in queries)

    @patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True)
    def test_public_overlap_saves_once(self):
        root = self.build('overlap', 1)
        file_obj = File.objects.filter(folder__parent=root).first()
        saved = []
        original_save = File.save

        def save(instance, *args, **kwargs):
            saved.append(instance.pk)
            return original_save(instance, *args, **kwargs)

        with patch.object(File, 'save', save), patch.object(self.folder_admin, 'message_user') as message:
            self.folder_admin.files_set_public(
                self.request(), File.objects.filter(pk=file_obj.pk), Folder.objects.filter(pk=root.pk),
            )

        self.assertEqual(saved.count(file_obj.pk), 1)
        self.assertIn(f'for {len(saved)} files.', str(message.call_args.args[1]))

    @patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True)
    def test_set_public_reads_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root = self.build(f'public {width}', width)
            selected = Folder.objects.filter(pk=root.pk)
            counts[width] = self.folder_reads(
                lambda: self.folder_admin.files_set_public(self.request(), File.objects.none(), selected),
            )

            subtree = [root.pk, *root.get_descendants_ids()]
            self.assertFalse(File.objects.filter(folder_id__in=subtree, is_public=False).exists())
        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])

    def test_move_to_clipboard_reads_follow_depth(self):
        counts = {}
        for width in (SMALL_WIDTH, LARGE_WIDTH):
            root = self.build(f'clip {width}', width)
            subtree = [root.pk, *root.get_descendants_ids()]
            expected = set(File.objects.filter(folder_id__in=subtree).values_list('pk', flat=True))
            selected = Folder.objects.filter(pk=root.pk)
            counts[width] = self.folder_reads(
                lambda: self.folder_admin.move_to_clipboard(self.request(), File.objects.none(), selected),
            )

            clipboard = Clipboard.objects.get(user=self.superuser)
            self.assertLessEqual(expected, set(clipboard.files.values_list('pk', flat=True)))
            self.assertFalse(File.objects.filter(pk__in=expected, folder__isnull=False).exists())
        self.assertEqual(counts[SMALL_WIDTH], counts[LARGE_WIDTH])


class TreeHelperTests(TestCase):
    def test_load_subtrees_stops_on_cycles(self):
        first = Folder.objects.create(name='first')
        second = Folder.objects.create(name='second', parent=first)
        # Corrupt data must not loop forever.
        Folder.objects.filter(pk=first.pk).update(parent=second)

        children, _ = load_subtrees([Folder.objects.get(pk=first.pk)])

        self.assertEqual({parent: [child.pk for child in kids] for parent, kids in children.items()}, {first.pk: [second.pk]})

    def test_share_source_needs_matching_key(self):
        source = Folder.objects.create(name='source')
        other = Folder.objects.create(name='other')
        child = Folder.objects.create(name='child', parent=other)

        NestedObjects(using='default')._share_source(source, child)
        self.assertEqual(child.parent, other)

        child.parent_id = source.pk
        NestedObjects(using='default')._share_source(source, child)
        self.assertIs(child.parent, source)

    def test_batches_without_backend_limit(self):
        folders = Folder.objects.bulk_create([Folder(name=f'batched {index}') for index in range(5)])
        ids = [folder.pk for folder in folders]

        # Backends without a declared limit still get bounded IN lists. Fake
        # only the lookup in tools; SQLite itself reads its real limit.
        unlimited = {'default': SimpleNamespace(features=SimpleNamespace(max_query_params=None))}
        with patch('filer.admin.tools.connections', unlimited), \
                patch('filer.admin.tools.BATCH_SIZE', 2), self.assertNumQueries(3):
            loaded = list(filter_in_batches(Folder.objects.all(), 'pk', ids))
        self.assertEqual(sorted(folder.pk for folder in loaded), ids)
