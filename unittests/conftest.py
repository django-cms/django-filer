import os
import pytest
import random
from uuid import uuid5, NAMESPACE_DNS

from django.conf import settings
from django.core.management import call_command
from django.urls import reverse

from finder.models.ambit import AmbitModel

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')


@pytest.fixture(autouse=True, scope='session')
def create_assets():
    os.makedirs(settings.BASE_DIR / 'workdir/assets', exist_ok=True)
    with open(settings.BASE_DIR / 'workdir/assets/small_file.bin', 'wb') as handle:
        handle.write(random.randbytes(1000))
    with open(settings.BASE_DIR / 'workdir/assets/huge_file.bin', 'wb') as handle:
        handle.write(random.randbytes(100000))


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    database_file = settings.BASE_DIR / 'workdir/test_db.sqlite3'
    try:
        os.remove(database_file)
    except FileNotFoundError:
        pass
    settings.DATABASES['default']['NAME'] = database_file
    with django_db_blocker.unblock():
        call_command('migrate', verbosity=0)
    yield
    os.remove(database_file)


@pytest.fixture(autouse=True, scope='session')
def ambit(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command(
            'finder',
            'add-root',
            'test-ambit',
            '--values',
            'name=Root Folder',
            'storage=finder_test',
            'sample_storage=finder_test_samples'
        )
        ambit = AmbitModel.objects.first()
        assert ambit is not None
        return ambit


@pytest.fixture(scope='session')
def root_folder_url(ambit):
    base_url = reverse('admin:app_list', kwargs={'app_label': 'finder'})
    return f'{base_url}{ambit.slug}/{ambit.root_folder_id}'


@pytest.fixture
def missing_inode_id():
    return uuid5(NAMESPACE_DNS, 'missing-inode')
