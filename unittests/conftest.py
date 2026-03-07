import os
import pytest
import random
from io import BytesIO
from uuid import uuid5, NAMESPACE_DNS

from PIL import Image, ImageDraw
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.urls import reverse

from finder.contrib.image.pil.models import PILImageModel
from finder.models.ambit import AmbitModel
from finder.models.file import FileModel

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
    """Prepare the test database for the session."""

    with django_db_blocker.unblock():
        db_settings = settings.DATABASES.get('default', {})
        engine = db_settings.get('ENGINE', '')

        # If using SQLite ensure the test DB file is removed so migrations start
        # from a clean slate.
        if 'sqlite3' in engine:
            db_name = db_settings.get('NAME')
            try:
                os.remove(db_name)
            except FileNotFoundError:
                pass
        else:
            with connection.cursor() as cursor:
                table_names = connection.introspection.table_names()
                for table_name in table_names:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')

        call_command('migrate', verbosity=0)
    yield


@pytest.fixture(autouse=True, scope='session')
def ambit(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command(
            'finder',
            'add-ambit',
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


@pytest.fixture
def uploaded_file(ambit, admin_user):
    file_name = 'small_file.bin'
    with open(settings.BASE_DIR / 'workdir/assets' / file_name, 'rb') as file_handle:
        uploaded_file = SimpleUploadedFile(file_name, file_handle.read(), content_type='application/octet-stream')
    return FileModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=ambit.root_folder,
        owner=admin_user,
    )


@pytest.fixture
def uploaded_image(ambit, admin_user):
    image = Image.new('RGB', (640, 480))
    draw = ImageDraw.Draw(image)
    for _ in range(20):
        x1, y1 = random.randint(0, 640), random.randint(0, 480)
        x2, y2 = random.randint(0, 640), random.randint(0, 480)
        color = tuple(random.randint(0, 255) for _ in range(3))
        draw.rectangle([x1, y1, x2, y2], fill=color)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    uploaded_file = SimpleUploadedFile('test_image.png', buffer.read(), content_type='image/png')
    return PILImageModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=ambit.root_folder,
        owner=admin_user,
    )

