from unittest.mock import patch

from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models.signals import post_init
from django.test import TestCase
from django.urls import reverse

from filer import settings as filer_settings
from filer.admin.pagination import FolderItems
from filer.cache import clear_folder_permission_cache
from filer.models import File, Folder, FolderPermission
from tests.helpers import create_superuser


PAGE_SIZE = 3


class DirectoryPaginationTests(TestCase):
    def setUp(self):
        self.user = create_superuser()
        self.client.force_login(self.user)
        page_size = patch('filer.admin.folderadmin.FILER_PAGINATE_BY', PAGE_SIZE)
        page_size.start()
        self.addCleanup(page_size.stop)
        self.parent = Folder.objects.create(name='parent', owner=self.user)
        self.folders = [
            Folder.objects.create(name=name, parent=self.parent, owner=self.user)
            for name in ('alpha', 'zeta')
        ]
        self.files = File.objects.bulk_create([
            File(name=f'file-{index}', folder=self.parent, owner=self.user)
            for index in range(8)
        ])
        self.url = reverse('admin:filer-directory_listing', args=(self.parent.pk,))

    def test_ties_break_on_pk(self):
        # Without a unique last key, OFFSET pages may overlap on equal names.
        for params in ({}, {'order_by': 'owner'}, {'order_by': ''}, {'order_by': 'bogus'}, {'q': 'file'}):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.context['folder_children'].query.order_by[-1], 'pk')
                self.assertEqual(response.context['folder_files'].query.order_by[-1], 'pk')
                if params.get('order_by') != 'owner':
                    # Without a valid sort, files fall back to the display name.
                    self.assertEqual(len(response.context['folder_files'].query.order_by), 2)

    def test_only_page_materialized(self):
        loaded = []

        def record_file(sender, instance, **kwargs):
            loaded.append(instance.pk)

        post_init.connect(record_file, sender=File)
        self.addCleanup(post_init.disconnect, record_file, sender=File)
        cases = (
            ({}, self.files[:1]),
            ({'page': 2}, self.files[1:4]),
            ({'q': 'file'}, self.files[:PAGE_SIZE]),
            ({'q': 'file', 'limit_search_to_folder': 'on'}, self.files[:PAGE_SIZE]),
        )
        for params, expected in cases:
            with self.subTest(params=params):
                loaded.clear()
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(loaded, [file.pk for file in expected])
                if params.get('q'):
                    self.assertContains(response, '8 files')

    def test_folder_file_page_order(self):
        cases = (
            (1, self.folders + self.files[:1]),
            (2, self.files[1:4]),
            (4, self.files[7:]),
            (999, self.files[7:]),
            (0, self.files[7:]),
            ('invalid', self.folders + self.files[:1]),
        )
        for page, expected in cases:
            with self.subTest(page=page):
                response = self.client.get(self.url, {'page': page})
                page_items = response.context['paginated_items']
                self.assertEqual(list(page_items), expected)
                self.assertEqual(page_items.paginator.count, len(self.folders) + len(self.files))

    def test_empty_search_page(self):
        response = self.client.get(self.url, {'q': 'not-found'})
        page = response.context['paginated_items']
        self.assertEqual(list(page), [])
        self.assertEqual(page.number, 1)
        self.assertEqual(page.paginator.count, 0)

    def test_file_order_is_preserved(self):
        response = self.client.get(self.url, {'q': 'file', 'order_by': '-name', 'page': 2})
        self.assertEqual(list(response.context['paginated_items']), list(reversed(self.files))[3:6])

    def test_actions_span_pages(self):
        destination = Folder.objects.create(name='destination', owner=self.user)
        response = self.client.post(self.url, {
            'action': 'move_files_and_folders',
            'post': 'yes',
            'destination': destination.pk,
            'select_across': '1',
            helpers.ACTION_CHECKBOX_NAME: f'file-{self.files[0].pk}',
        })
        self.assertEqual(response.status_code, 302)
        self.assertCountEqual(File.objects.filter(folder=destination), self.files)
        self.assertCountEqual(Folder.objects.filter(parent=destination), self.folders)

    def test_item_sequence(self):
        items = FolderItems(
            Folder.objects.filter(parent=self.parent).order_by('name'),
            File.objects.filter(folder=self.parent).order_by('name'),
        )
        expected = self.folders + self.files
        for key in (0, 2, -1, -10, slice(None), slice(1, 5), slice(7, 2), slice(None, None, -1), slice(1, 9, 2)):
            with self.subTest(key=key):
                self.assertEqual(items[key], expected[key])
        for key in (len(expected), -len(expected) - 1):
            with self.assertRaises(IndexError):
                _ = items[key]

    def test_permission_page_counts(self):
        user = get_user_model().objects.create(username='reader', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='can_use_directory_listing'))
        clear_folder_permission_cache(user)
        self.addCleanup(clear_folder_permission_cache, user)
        FolderPermission.objects.create(
            user=user, folder=self.folders[0], type=FolderPermission.THIS,
            can_read=FolderPermission.ALLOW,
        )
        File.objects.filter(pk__in=[file.pk for file in self.files[:4]]).update(owner=user)
        self.client.force_login(user)

        with patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True):
            response = self.client.get(self.url, {'page': 2})

        page = response.context['paginated_items']
        self.assertEqual(page.paginator.count, 5)
        self.assertEqual(list(page), self.files[2:4])
