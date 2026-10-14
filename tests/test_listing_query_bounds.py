import os
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files import File as DjangoFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from filer import settings as filer_settings
from filer.cache import clear_folder_permission_cache
from filer.models import File, Folder, FolderPermission
from filer.settings import FILER_IMAGE_MODEL, TABLE_LIST_TYPE, THUMBNAIL_LIST_TYPE
from filer.utils.loader import load_model
from tests.helpers import create_image, create_superuser


Image = load_model(FILER_IMAGE_MODEL)

SMALL_COUNT = 2
LARGE_COUNT = 12
LIST_TYPES = (TABLE_LIST_TYPE, THUMBNAIL_LIST_TYPE)
# Browsing loads rows through related managers; search loads them directly.
BROWSE = 'browse'
SEARCH = 'search'
MODES = (BROWSE, SEARCH)


def count_queries(func):
    with CaptureQueriesContext(connection) as queries:
        result = func()
    return result, len(queries)


class ListingMixin:
    def listing(self, folder, mode, token, **params):
        # Search runs from the parent folder, so rows come from plain querysets.
        if mode == SEARCH:
            folder, params['q'] = folder.parent, token
        return self.client.get(reverse('admin:filer-directory_listing', args=(folder.pk,)), params)


class FileRowQueryTests(ListingMixin, TestCase):
    def setUp(self):
        permissions = patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True)
        permissions.start()
        self.addCleanup(permissions.stop)

        self.owner = create_superuser()
        self.user = get_user_model().objects.create_user(username='staff', password='x', is_staff=True)
        self.user.user_permissions.add(*Permission.objects.filter(
            codename__in=('change_file', 'change_folder', 'can_use_directory_listing'),
        ))
        clear_folder_permission_cache(self.user)
        self.addCleanup(clear_folder_permission_cache, self.user)
        self.client.login(username='staff', password='x')

        self.image_path = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, 'listing.jpg')
        create_image().save(self.image_path, 'JPEG')
        self.addCleanup(os.remove, self.image_path)

    def build(self, token, count, grant):
        parent = Folder.objects.create(name=f'parent{token}', owner=self.owner)
        folder = Folder.objects.create(name=f'folder{token}', parent=parent, owner=self.owner)
        for granted in (parent, folder):
            FolderPermission.objects.create(
                user=self.user, folder=granted, type=FolderPermission.THIS,
                can_read=FolderPermission.ALLOW, can_edit=grant,
            )
        files = [
            File.objects.create(original_filename=f'{token}x{index}.txt', folder=folder, owner=self.owner)
            for index in range(count)
        ]
        with open(self.image_path, 'rb') as handle:
            files.append(Image.objects.create(
                original_filename=f'{token}.jpg', folder=folder, owner=self.owner,
                file=DjangoFile(handle, name=f'{token}.jpg'), mime_type='image/jpeg',
            ))
        clear_folder_permission_cache(self.user)
        return folder, files

    def test_edit_links_follow_permission(self):
        grants = ((FolderPermission.ALLOW, True), (FolderPermission.DENY, False))
        for mode in MODES:
            for list_type in LIST_TYPES:
                for grant, visible in grants:
                    with self.subTest(mode=mode, list_type=list_type, grant=grant):
                        token = f'{mode}{list_type}{grant}'
                        folder, files = self.build(token, SMALL_COUNT, grant)
                        response = self.listing(folder, mode, token, _list_type=list_type)

                        content = response.content.decode()
                        for file_obj in files:
                            self.assertIn(file_obj.label, content)
                            self.assertEqual(file_obj.get_admin_change_url() in content, visible)

    def test_file_queries_follow_page(self):
        for mode in MODES:
            for list_type in LIST_TYPES:
                counts = {}
                for count in (SMALL_COUNT, LARGE_COUNT):
                    token = f'{mode}{list_type}{count}'
                    folder, files = self.build(token, count, FolderPermission.ALLOW)
                    # Warm content type and permission caches outside the measurement.
                    self.listing(folder, mode, token, _list_type=list_type)
                    response, counts[count] = count_queries(
                        lambda: self.listing(folder, mode, token, _list_type=list_type),
                    )

                    self.assertContains(response, files[-1].get_admin_change_url())

                with self.subTest(mode=mode, list_type=list_type):
                    self.assertEqual(counts[SMALL_COUNT], counts[LARGE_COUNT])


class PickFolderQueryTests(ListingMixin, TestCase):
    def setUp(self):
        create_superuser()
        self.client.login(username='admin', password='secret')

    def build(self, token, count):
        parent = None
        for depth in range(3):
            parent = Folder.objects.create(name=f'{token}d{depth}', parent=parent)
        for index in range(count):
            Folder.objects.create(name=f'{token}s{index}', parent=parent)
        return parent

    def test_pick_labels_follow_page(self):
        for list_type in LIST_TYPES:
            for mode in MODES:
                counts = {}
                for count in (SMALL_COUNT, LARGE_COUNT):
                    token = f'{list_type}{mode}{count}'
                    folder = self.build(token, count)
                    pick = {'_pick': 'folder', '_popup': '1', '_list_type': list_type}
                    self.listing(folder, mode, f'{token}s', **pick)
                    response, counts[count] = count_queries(
                        lambda: self.listing(folder, mode, f'{token}s', **pick),
                    )

                    path = '/'.join(f'{token}d{depth}' for depth in range(3))
                    for index in range(count):
                        self.assertContains(response, f'data-label="/{path}/{token}s{index}"')

                with self.subTest(list_type=list_type, mode=mode):
                    self.assertEqual(counts[SMALL_COUNT], counts[LARGE_COUNT])
