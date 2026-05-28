import os
import pytest
import random
from io import BytesIO
from uuid import uuid5, NAMESPACE_DNS

from PIL import Image, ImageDraw
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.urls import reverse

from finder.contrib.image.pil.models import PILImageModel
from finder.models.ambit import AmbitModel
from finder.models.file import FileModel
from finder.models.folder import FolderModel
from finder.models.permission import Privilege

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')


@pytest.fixture(scope='session', autouse=True)
def create_assets():
    os.makedirs(settings.BASE_DIR / 'workdir/assets', exist_ok=True)
    with open(settings.BASE_DIR / 'workdir/assets/small_file.bin', 'wb') as handle:
        handle.write(random.randbytes(1000))
    with open(settings.BASE_DIR / 'workdir/assets/huge_file.bin', 'wb') as handle:
        handle.write(random.randbytes(100000))


@pytest.fixture
def staff_users():
    User = get_user_model()
    users = User.objects.bulk_create([
        User(username='alice', is_staff=True),
        User(username='bob', is_staff=True),
        User(username='charlie', is_staff=True),
    ])
    return users


@pytest.fixture
def groups():
    return Group.objects.bulk_create([
        Group(name='Editors'),
        Group(name='Reviewers'),
        Group(name='Designers'),
    ])


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Prepare the test database for the session."""

    with django_db_blocker.unblock():
        db_settings = settings.DATABASES.get('default', {})
        engine = db_settings.get('ENGINE', '')

        # If using SQLite ensure the test DB file is removed so migrations start
        # from a clean slate.
        if 'sqlite3' in engine:  # pragma: with postgres
            db_name = db_settings.get('NAME')
            try:
                os.remove(db_name)
            except FileNotFoundError:  # pragma: no cover
                pass
        else:  # pragma: without postgres
            with connection.cursor() as cursor:
                table_names = connection.introspection.table_names()
                for table_name in table_names:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')

        call_command('migrate', verbosity=0)
    yield


def _ensure_ambit(django_db_blocker, slug, storage, sample_storage):
    """Re-create an ambit if it was flushed by a previous transaction=True test."""
    with django_db_blocker.unblock():
        if not AmbitModel.objects.filter(slug=slug).exists():
            call_command(
                'finder',
                'add-ambit',
                slug,
                '--values',
                'name=Root Folder',
                f'storage={storage}',
                f'sample_storage={sample_storage}',
            )
        return AmbitModel.objects.get(slug=slug)


@pytest.fixture
def ambit(django_db_blocker):
    return _ensure_ambit(django_db_blocker, 'test-ambit', 'finder_test', 'finder_test_samples')


@pytest.fixture
def alternative_ambit(django_db_blocker):
    return _ensure_ambit(django_db_blocker, 'alternative-ambit', 'finder_alternative', 'finder_alternative_samples')


@pytest.fixture
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
        x0, y0 = random.randint(0, 630), random.randint(0, 470)
        x1, y1 = random.randint(x0 + 1, 640), random.randint(y0 + 1, 480)
        color = tuple(random.randint(0, 255) for _ in range(3))
        draw.rectangle([x0, y0, x1, y1], fill=color)
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


@pytest.fixture
def sub_folder(ambit, admin_user):
    return FolderModel.objects.create(
        parent=ambit.root_folder,
        name='Sub Folder',
        owner=admin_user,
    )


@pytest.fixture(params=['superuser', 'user', 'group', 'everyone'])
def principal_kwargs(admin_user, request):
    if request.param == 'superuser':
        return
    admin_user.is_superuser = False
    admin_user.save(update_fields=['is_superuser'])
    if request.param == 'user':
        return {'user': admin_user, 'privilege': Privilege.READ_WRITE}
    if request.param == 'group':
        group = admin_user.groups.create(name='Test Group')
        admin_user.groups.add(group)
        return {'group': group, 'privilege': Privilege.READ_WRITE}
    if request.param == 'everyone':
        return {'privilege': Privilege.READ_WRITE}
