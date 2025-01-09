import os
import pytest

from django.conf import settings
from django.core.management import call_command
from django.contrib.admin.sites import site as admin_site
from django.urls import reverse

from finder.models.folder import FolderModel

from .utils import create_random_image

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')


@pytest.fixture(autouse=True, scope='session')
def create_assets():
    os.makedirs(settings.BASE_DIR / 'workdir/assets', exist_ok=True)
    image = create_random_image()
    image.save(settings.BASE_DIR / 'workdir/assets/demo_image.png')


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    database_file = settings.BASE_DIR / 'workdir/test_db.sqlite3'
    settings.DATABASES['default']['NAME'] = database_file
    with django_db_blocker.unblock():
        call_command('migrate', verbosity=0)
    yield
    os.remove(database_file)


@pytest.fixture
def realm(rf, admin_user):
    folder_admin = admin_site.get_model_admin(FolderModel)
    request = rf.get(reverse('admin:finder_foldermodel_changelist'))
    request.user = admin_user
    return folder_admin.get_realm(request)
