import os
import pytest

from playwright.sync_api import sync_playwright

from django.conf import settings
from django.core.management import call_command
from django.urls import reverse

from finder.models.realm import RealmModel


os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')


@pytest.fixture(autouse=True, scope='session')
def create_assets():
    os.makedirs(settings.BASE_DIR / 'workdir/assets', exist_ok=True)
    for counter in range(10):
        image = create_random_image()
        image.save(settings.BASE_DIR / 'workdir/assets' / f'image_{counter:01d}.png')


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    database_file = settings.BASE_DIR / 'workdir/test_db.sqlite3'
    settings.DATABASES['default']['NAME'] = database_file
    with django_db_blocker.unblock():
        call_command('migrate', verbosity=0)
    yield
    os.remove(database_file)


@pytest.fixture
def realm(admin_client):
    if realm := RealmModel.objects.first():
        return realm
    response = admin_client.get(reverse('admin:finder_foldermodel_changelist'))
    assert response.status_code == 302
    realm = RealmModel.objects.first()
    assert realm is not None
    redirected = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id})
    assert response.url == redirected
    assert realm.root_folder.is_folder is True
    assert realm.root_folder.is_trash is False
    assert realm.root_folder.owner == response.wsgi_request.user
    assert realm.root_folder.name == '__root__'
    assert realm.root_folder.parent is None
    assert realm.root_folder.is_root
    assert realm.trash_folders.count() == 0
    return realm


class Connector:
    def __init__(self, live_server):
        print(f"\nStarting end-to-end test server at {live_server}\n")
        self.live_server = live_server

    def __enter__(self):
        def print_args(msg):
            if msg.type in ['info', 'debug']:
                return
            for arg in msg.args:
                print(arg.json_value())

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.browser.close()
        self.playwright.stop()


@pytest.fixture(scope='session')
def connector(live_server):
    with Connector(live_server) as connector:
        yield connector


@pytest.fixture
def locale():
    return 'en-US'


@pytest.fixture
def language():
    return 'en'


def print_args(msg):
    """
    Print messages from the browser console.
    """
    for arg in msg.args:
        print(arg.json_value())


@pytest.fixture()
def page(connector, viewname, locale, language):
    context = connector.browser.new_context(locale=locale)
    context.add_cookies([{'name': 'django_language', 'value': language, 'domain': 'localhost', 'path': '/'}])
    page = context.new_page()
    # page.on('console', print_args)
    page.goto(connector.live_server.url + reverse(viewname))
    # django_formset = page.locator('django-formset:defined')
    # django_formset.wait_for()
    return page
