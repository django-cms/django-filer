"""Measure tree and search workloads on a source snapshot; see README.md."""

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns


WARMUPS = 2
SAMPLES = 5


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def measure(name, size, operation, prepare):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    samples, prints = [], set()
    for index in range(WARMUPS + SAMPLES):
        prepare()
        start = perf_counter_ns()
        result = operation()
        elapsed = (perf_counter_ns() - start) / 1_000_000
        prints.add(fingerprint(result))
        if index >= WARMUPS:
            samples.append(elapsed)
    prepare()
    with CaptureQueriesContext(connection) as queries:
        prints.add(fingerprint(operation()))
    assert len(prints) == 1, (name, size)
    return {'name': name, 'size': size, 'samples_ms': samples, 'queries': len(queries), 'fingerprint': prints.pop()}


def html(response):
    assert response.status_code == 200, response.status_code
    # CSRF masks change on every response; keep all other rendered HTML.
    return re.sub(r'(name="csrfmiddlewaretoken" value=")[^"]+', r'\1TOKEN', response.content.decode())


def build_tree(width, files=False):
    from filer.models import File, Folder

    root = Folder.objects.create(name='root')
    children = Folder.objects.bulk_create([Folder(name=f'child-{i:04}', parent=root) for i in range(width)])
    leaves = Folder.objects.bulk_create([Folder(name=f'leaf-{i:04}', parent=child) for i, child in enumerate(children)])
    if files:
        File.objects.bulk_create([File(original_filename=f'f-{i:04}.txt', folder=leaf, _file_size=1) for i, leaf in enumerate(leaves)])
    return root


def staff(*codenames):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Permission

    user = get_user_model().objects.create_user(username='staff', password='x', is_staff=True)
    user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))
    return user


def fresh_request(user):
    from django.contrib.auth import get_user_model
    from django.test import RequestFactory

    request = RequestFactory().post('/')
    request.user = get_user_model().objects.get(pk=user.pk)
    return request


def case(name, size):
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.urls import reverse

    from filer.cache import clear_folder_permission_cache
    from filer.models import File, Folder, FolderPermission

    noop = lambda: None  # noqa: E731
    superuser = get_user_model().objects.create_superuser('admin', 'a@b.c', 'secret')
    client = Client()

    if name == 'descendant_ids':
        root = build_tree(size)
        return lambda: sorted(root.get_descendants_ids()), noop

    if name == 'limited_search':
        root = build_tree(size, files=True)
        client.force_login(superuser)
        url = reverse('admin:filer-directory_listing', args=(root.pk,))
        return lambda: html(client.get(url, {'q': 'f-', 'limit_search_to_folder': 'on'})), noop

    if name in ('edit_check', 'destinations'):
        from django.contrib import admin

        from filer.admin.tools import check_folder_edit_permissions

        root = build_tree(size, files=True)
        user = staff('change_folder', 'change_file')
        FolderPermission.objects.create(
            user=user, folder=root, type=FolderPermission.CHILDREN,
            can_read=FolderPermission.ALLOW, can_edit=FolderPermission.ALLOW, can_add_children=FolderPermission.ALLOW,
        )
        prepare = lambda: clear_folder_permission_cache(user)  # noqa: E731
        if name == 'edit_check':
            return lambda: check_folder_edit_permissions(fresh_request(user), [root]) or 'allowed', prepare

        folder_admin = admin.site._registry[Folder]

        def destinations():
            choices = folder_admin._list_all_destination_folders(fresh_request(user), Folder.objects.none(), None, False)
            return [(folder.pk, str(label), enabled) for folder, (label, enabled) in choices]
        return destinations, prepare

    if name == 'delete_confirmation':
        root = build_tree(size, files=True)
        client.force_login(superuser)
        url = reverse('admin:filer-directory_listing-root')
        data = {'action': 'delete_files_or_folders', '_selected_action': [f'folder-{root.pk}']}
        return lambda: html(client.post(url, data)), noop

    if name == 'move_listing':
        from django.contrib import admin

        root = build_tree(size, files=True)
        folder_admin = admin.site._registry[Folder]

        def listing():
            request = fresh_request(superuser)
            return [str(item) for item in folder_admin._list_all_to_copy_or_move(
                request, File.objects.none(), Folder.objects.filter(pk=root.pk))]
        return listing, noop

    if name == 'search_files':
        user = staff('change_file', 'change_folder', 'can_use_directory_listing')
        folder = Folder.objects.create(name='docs')
        FolderPermission.objects.create(
            user=user, folder=folder, type=FolderPermission.THIS,
            can_read=FolderPermission.ALLOW, can_edit=FolderPermission.ALLOW,
        )
        File.objects.bulk_create([File(original_filename=f'f-{i:04}.txt', folder=folder, owner=superuser, _file_size=1) for i in range(size)])
        client.force_login(user)
        url = reverse('admin:filer-directory_listing', args=(folder.pk,))
        return lambda: html(client.get(url, {'q': 'f-'})), lambda: clear_folder_permission_cache(user)

    if name == 'pick_search_folders':
        parent = None
        for depth in range(3):
            parent = Folder.objects.create(name=f'level-{depth}', parent=parent)
        Folder.objects.bulk_create([Folder(name=f'pick-{i:04}', parent=parent) for i in range(size)])
        client.force_login(superuser)
        url = reverse('admin:filer-directory_listing', args=(parent.pk,))
        return lambda: html(client.get(url, {'q': 'pick-', '_pick': 'folder', '_popup': '1', '_list_type': 'tb'})), noop

    raise ValueError(name)


def run_cases():
    from unittest.mock import patch

    from django.core.cache import cache
    from django.db import transaction

    from filer import settings as filer_settings

    names = ('descendant_ids', 'limited_search', 'edit_check', 'destinations',
             'delete_confirmation', 'move_listing', 'search_files', 'pick_search_folders')
    sizes = {'search_files': (25, 100), 'pick_search_folders': (25, 100)}
    results = []
    with patch.object(filer_settings, 'FILER_ENABLE_PERMISSIONS', True):
        with patch('filer.admin.folderadmin.FILER_PAGINATE_BY', 100):
            for name in names:
                for size in sizes.get(name, (50, 200)):
                    cache.clear()
                    with transaction.atomic():
                        operation, prepare = case(name, size)
                        results.append(measure(name, size, operation, prepare))
                        transaction.set_rollback(True)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    sys.path.insert(0, str(source))
    os.chdir(source)
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    import django
    from django.core.management import call_command
    from django.db import connection
    from django.test import override_settings

    from app_helper.runner import setup
    from tests import settings as test_settings

    from filer import __file__ as filer_path

    assert Path(filer_path).resolve().is_relative_to(source), filer_path
    setup('filer', test_settings)
    call_command('migrate', verbosity=0, interactive=False)
    with override_settings(ALLOWED_HOSTS=['testserver'], DEBUG=False,
                           SESSION_ENGINE='django.contrib.sessions.backends.cache'):
        results = run_cases()
    output.write_text(json.dumps({
        'source': str(source), 'revision': args.revision, 'python': platform.python_version(),
        'django': django.get_version(), 'polymorphic': version('django-polymorphic'),
        'platform': platform.platform(), 'sqlite': connection.Database.sqlite_version,
        'warmups': WARMUPS, 'samples': SAMPLES, 'results': results,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
