"""Measure a source snapshot; see README.md for paired-run instructions."""

import argparse
import hashlib
import json
import os
import platform
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns


WARMUPS = 2
SAMPLES = 5
PAGE_SIZE = 100
FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def measure(name, size, operation, prepare):
    from django.db import connection, reset_queries
    from django.db.models.signals import post_init
    from django.test.utils import CaptureQueriesContext

    from filer.models import File, Folder

    samples = []
    fingerprints = set()
    for index in range(WARMUPS + SAMPLES):
        prepare()
        start = perf_counter_ns()
        result = operation()
        elapsed = (perf_counter_ns() - start) / 1_000_000
        fingerprints.add(fingerprint(result))
        if index >= WARMUPS:
            samples.append(elapsed)

    loaded = Counter()

    def record(sender, **kwargs):
        loaded[sender.__name__] += 1

    # SQL and model instrumentation stay outside the timed samples.
    prepare()
    reset_queries()
    post_init.connect(record, sender=File)
    post_init.connect(record, sender=Folder)
    try:
        with CaptureQueriesContext(connection) as queries:
            result = operation()
        fingerprints.add(fingerprint(result))
    finally:
        post_init.disconnect(record, sender=File)
        post_init.disconnect(record, sender=Folder)
    assert len(fingerprints) == 1, (name, size, fingerprints)
    return {
        'name': name, 'size': size, 'samples_ms': samples, 'queries': len(queries),
        'objects': dict(loaded), 'fingerprint': fingerprints.pop(),
    }


def listing_case(name, size):
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.urls import reverse

    from filer.models import File, Folder

    user = get_user_model().objects.create(username='admin', is_staff=True, is_superuser=True)
    parent = Folder.objects.create(name='parent', owner=user)
    if name == 'folder_counts':
        folders = Folder.objects.bulk_create([
            Folder(name=f'folder-{index:05}', parent=parent, owner=user) for index in range(size)
        ])
        Folder.objects.bulk_create([Folder(name='child', parent=folder, owner=user) for folder in folders])
        File.objects.bulk_create([File(name='file', folder=folder, owner=user, _file_size=1) for folder in folders])
    else:
        File.objects.bulk_create([
            File(name=f'file-{index:05}', folder=parent, owner=user, _file_size=1) for index in range(size)
        ])
    Folder.objects.update(uploaded_at=FIXED_TIME, created_at=FIXED_TIME, modified_at=FIXED_TIME)
    File.objects.update(uploaded_at=FIXED_TIME, modified_at=FIXED_TIME)
    client = Client()
    client.force_login(user)
    url = reverse('admin:filer-directory_listing', args=(parent.pk,))
    params = {'q': 'file'} if name == 'search' else {}

    def request():
        response = client.get(url, params)
        assert response.status_code == 200, response.status_code
        # CSRF masks change on every response; retain all other rendered HTML.
        return re.sub(r'(name="csrfmiddlewaretoken" value=")[^"]+', r'\1TOKEN', response.content.decode())

    return request, lambda: None


def permission_case(name, size):
    from django.contrib.auth import get_user_model

    from filer.cache import clear_folder_permission_cache
    from filer.models import Folder, FolderPermission

    user = get_user_model().objects.create(username='reader')
    folders = []
    parent = None
    for index in range(size):
        parent = Folder.objects.create(name=f'level-{index}', parent=parent)
        folders.append(parent)
    roots = folders if name == 'overlapping_grants' else folders[:1]
    if name == 'empty_permissions':
        roots = []
    FolderPermission.objects.bulk_create([
        FolderPermission(user=user, folder=root, type=FolderPermission.CHILDREN, can_read=FolderPermission.ALLOW)
        for root in roots
    ])

    def read():
        if name == 'empty_permissions':
            return [sorted(FolderPermission.objects.get_read_id_list(user)) for _ in range(size)]
        result = sorted(FolderPermission.objects.get_read_id_list(user))
        assert result == sorted(folder.pk for folder in folders)
        return result

    def prepare():
        clear_folder_permission_cache(user)
        if name == 'empty_permissions':
            FolderPermission.objects.get_read_id_list(user)

    return read, prepare


def duplicate_case(name, size):
    from filer.models import File

    digests = ['shared'] * size
    if name == 'mostly_unique':
        digests = ['shared', 'shared'] + [f'unique-{index}' for index in range(size - 2)]
    File.objects.bulk_create([
        File(name=f'file-{index}', sha1=digest, _file_size=1) for index, digest in enumerate(digests)
    ])

    def duplicates():
        # Consume every group so eager and lazy implementations do equal work.
        return {
            digest: sorted(file.pk for file in files)
            for digest, files in File.objects.find_all_duplicates().items()
        }

    return duplicates, lambda: None


def run_cases():
    from unittest.mock import patch

    from django.core.cache import cache
    from django.db import transaction

    import filer

    cases = (
        ('listing', (100, 1000, 10000), listing_case),
        ('search', (100, 1000, 10000), listing_case),
        ('folder_counts', (25, 100), listing_case),
        ('overlapping_grants', (25, 50, 100), permission_case),
        ('single_root', (25, 50, 100), permission_case),
        ('empty_permissions', (100, 1000), permission_case),
        ('duplicates', (100, 200, 400), duplicate_case),
        ('mostly_unique', (100, 400), duplicate_case),
    )
    results = []
    with patch.object(filer.settings, 'FILER_ENABLE_PERMISSIONS', True):
        with patch('filer.admin.folderadmin.FILER_PAGINATE_BY', PAGE_SIZE):
            for name, sizes, setup in cases:
                for size in sizes:
                    cache.clear()
                    with transaction.atomic():
                        operation, prepare = setup(name, size)
                        results.append(measure(name, size, operation, prepare))
                        transaction.set_rollback(True)
                    print(f'{name} {size}: done', file=sys.stderr, flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    sys.path.insert(0, str(source))
    os.chdir(source)
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    import django
    from django.core.management import call_command
    from django.db import connection
    from django.test import override_settings

    from app_helper.runner import setup
    from tests import settings as test_settings

    # Use one import style for filer; CodeQL flags mixing both.
    from filer import __file__ as filer_path

    assert Path(filer_path).resolve().is_relative_to(source), filer_path
    setup('filer', test_settings)
    assert connection.settings_dict['NAME'] == ':memory:'
    call_command('migrate', verbosity=0, interactive=False)
    with override_settings(
        ALLOWED_HOSTS=['testserver'], DEBUG=False,
        SESSION_ENGINE='django.contrib.sessions.backends.cache',
    ):
        results = run_cases()
    output.write_text(json.dumps({
        'source': str(source), 'revision': args.revision, 'python': platform.python_version(),
        'django': django.get_version(), 'polymorphic': version('django-polymorphic'),
        'platform': platform.platform(), 'sqlite': connection.Database.sqlite_version,
        'warmups': WARMUPS, 'samples': SAMPLES, 'results': results,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
