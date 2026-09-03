import os
import random
from collections import namedtuple
from io import StringIO
from colorsys import hls_to_rgb, rgb_to_hls

import pytest
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse

from finder.contrib.image.pil.models import PILImageModel
from finder.models.ambit import AmbitModel
from finder.models.folder import FolderModel

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

#: The ambit referred to by the ``FinderFileField``/``FinderFolderField`` of ``DemoAppModel``.
AMBIT_SLUG = 'public'

#: Number of sample images written to ``workdir/e2e/assets``.
NUM_SAMPLE_IMAGES = 10


class ColorRGB(namedtuple('ColorRGB', ['red', 'green', 'blue'])):
    """A RGB triple which can be shifted in luminance and hue."""

    def set_lum(self, lum: float) -> 'ColorRGB':
        hue, _, sat = rgb_to_hls(self.red / 255.0, self.green / 255.0, self.blue / 255.0)
        lum = min(max(lum, 0.0), 255.0)
        return self._replace(**dict(zip(
            self._fields,
            (int(c * 255) for c in hls_to_rgb(hue, lum / 255.0, sat)),
        )))

    def rotate_hue(self, degrees: float) -> 'ColorRGB':
        hue, lum, sat = rgb_to_hls(self.red / 255.0, self.green / 255.0, self.blue / 255.0)
        hue = (hue + degrees / 360.0) % 1.0
        return self._replace(**dict(zip(
            self._fields,
            (int(c * 255) for c in hls_to_rgb(hue, lum, sat)),
        )))


def create_random_image(width: int = 320, height: int = 240, gap: int = 10, seed=None) -> Image.Image:
    """
    Create a colourful mosaic image of the given size and return it as a PIL image.

    Passing a ``seed`` makes the result reproducible, which keeps the checksums of
    the generated assets stable across test runs.
    """
    rand = random.Random(seed)
    image = Image.new('RGB', (width, height), color=(0, 0, 0))
    drawing = ImageDraw.Draw(image)
    drawing.rectangle([(gap, gap), (width - gap, height - gap)], fill=(255, 255, 255))

    line_color = ColorRGB(red=30, green=150, blue=10)
    for y in range(2 * gap, height - gap, 2 * gap):
        color = line_color = line_color.set_lum(rand.gauss(128, 50))
        for x in range(2 * gap, width - gap, 2 * gap):
            color = color.rotate_hue(rand.randint(-15, 25))
            drawing.rectangle([(x, y), (x + gap, y + gap)], fill=tuple(color))
    return image


@pytest.fixture(scope='session')
def assets_dir():
    path = settings.BASE_DIR / 'workdir/e2e/assets'
    os.makedirs(path, exist_ok=True)
    return path


@pytest.fixture(autouse=True, scope='session')
def create_assets(assets_dir):
    """Write the sample files which the upload tests push into the browser."""
    for counter in range(NUM_SAMPLE_IMAGES):
        image = create_random_image(seed=counter)
        image.save(assets_dir / f'image_{counter:01d}.png')
    with open(assets_dir / 'sample_file.bin', 'wb') as handle:
        handle.write(random.Random(0).randbytes(1000))
    return assets_dir


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    db_settings = settings.DATABASES['default']
    if 'sqlite3' in db_settings['ENGINE']:
        os.makedirs(os.path.dirname(db_settings['NAME']), exist_ok=True)
        try:
            os.remove(db_settings['NAME'])
        except FileNotFoundError:
            pass
    with django_db_blocker.unblock():
        call_command('migrate', verbosity=0)
    yield


@pytest.fixture
def admin_user(db, django_user_model):
    """
    The user which ``demoapp.middleware.AutoLoginMiddleware`` logs in.

    That middleware picks the first user in the database, so this fixture creates
    it up front. This keeps the browser session deterministic and gives the tests
    an owner for the objects they set up.
    """
    user, _ = django_user_model.objects.get_or_create(
        username='admin',
        defaults={'is_staff': True, 'is_superuser': True},
    )
    return user


@pytest.fixture
def ambit(admin_user):
    """
    The ambit holding the folder tree the demo app refers to.

    End-to-end tests run with ``transaction=True``, which flushes the database
    after every test, hence the ambit is re-created whenever it is missing.
    """
    if ambit := AmbitModel.objects.filter(slug=AMBIT_SLUG).first():
        return ambit
    call_command(
        'finder',
        'add-ambit',
        AMBIT_SLUG,
        '--values',
        'name=Root Folder',
        'storage=finder_demo',
        'sample_storage=finder_demo_samples',
        stdout=StringIO(),
    )
    return AmbitModel.objects.get(slug=AMBIT_SLUG)


@pytest.fixture
def root_folder(ambit):
    return ambit.root_folder


@pytest.fixture
def sub_folder(root_folder, admin_user):
    return FolderModel.objects.create(parent=root_folder, name='Sub Folder', owner=admin_user)


@pytest.fixture
def image_file(ambit, root_folder, admin_user, assets_dir):
    """An image sitting in the root folder, created without involving the browser."""
    with open(assets_dir / 'image_0.png', 'rb') as handle:
        uploaded_file = SimpleUploadedFile('image_0.png', handle.read(), content_type='image/png')
    return PILImageModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=root_folder,
        owner=admin_user,
    )


@pytest.fixture
def folder_admin_url(ambit):
    """URL of the React based folder admin, showing the root folder of ``ambit``."""
    base_url = reverse('admin:app_list', kwargs={'app_label': 'finder'})
    return f'{base_url}{ambit.slug}/{ambit.root_folder_id}'


class Connector:
    """Owns the Playwright driver and the browser shared by the whole session."""

    def __init__(self, live_server):
        self.live_server = live_server

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=os.getenv('PLAYWRIGHT_HEADED', '') not in ['1', 'true', 'True'],
            slow_mo=int(os.getenv('PLAYWRIGHT_SLOW_MO', '0')),
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.browser.close()
        self.playwright.stop()

    def url(self, path):
        return f'{self.live_server.url}{path}'


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


@pytest.fixture(scope='session')
def traces_dir():
    path = settings.BASE_DIR / 'workdir/e2e/traces'
    os.makedirs(path, exist_ok=True)
    return path


@pytest.fixture
def context(request, connector, locale, language, traces_dir):
    context = connector.browser.new_context(locale=locale, viewport={'width': 1280, 'height': 900})
    context.add_cookies([{
        'name': 'django_language',
        'value': language,
        'domain': 'localhost',
        'path': '/',
    }])
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield context
    # Keep a trace of failing tests only; open it with `playwright show-trace <file>`.
    if getattr(request.node, 'failed', False):
        context.tracing.stop(path=traces_dir / f'{request.node.name}.zip')
    else:
        context.tracing.stop()
    context.close()


@pytest.fixture
def page_errors():
    """Uncaught exceptions and ``console.error`` calls collected from the browser."""
    return []


@pytest.fixture
def server_errors():
    """Responses the live server answered with a status of 500 or above."""
    return []


def _is_javascript_error(message):
    # Chromium logs every unsuccessful request as a console error. Those are not
    # client-side errors: the finder deliberately answers with 4xx in some cases
    # and handles that in the client. Server errors are caught by ``server_errors``.
    return not message.startswith('Failed to load resource')


@pytest.fixture
def page(context, page_errors, server_errors):
    """A blank page which records JavaScript errors raised by the client code."""
    page = context.new_page()
    page.on('pageerror', lambda exc: page_errors.append(f'{exc}'))
    page.on(
        'console',
        lambda msg: msg.type == 'error' and _is_javascript_error(msg.text) and page_errors.append(msg.text),
    )
    page.on(
        'response',
        lambda response: response.status >= 500 and server_errors.append(f'{response.status} {response.url}'),
    )
    yield page
    page.close()


@pytest.fixture
def viewname():
    """The view ``demoapp_page`` navigates to. Override it to visit another view."""
    return 'demoapp'


@pytest.fixture
def demoapp_page(page, connector, ambit, viewname):
    """A page showing the demo form with its ``<finder-file-select>`` widget."""
    page.goto(connector.url(reverse(viewname)))
    return page


@pytest.fixture
def folder_admin_page(page, connector, folder_admin_url):
    """A page showing the React based folder admin of the root folder."""
    page.goto(connector.url(folder_admin_url))
    page.wait_for_selector('#content-react ul.inode-list, #content-react div.status')
    return page


@pytest.fixture(autouse=True)
def fail_on_browser_errors(request, page_errors, server_errors):
    """
    Turn uncaught client-side exceptions and server errors into test failures.

    Mark a test with ``@pytest.mark.allow_js_errors`` to opt out.
    """
    yield
    assert server_errors == [], f'The live server responded with errors: {server_errors}'
    if request.node.get_closest_marker('allow_js_errors'):
        return
    assert page_errors == [], f'The browser reported JavaScript errors: {page_errors}'


def pytest_configure(config):
    config.addinivalue_line('markers', 'allow_js_errors: do not fail the test on client-side errors')


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Remember whether a test failed, so that ``context`` can keep its trace."""
    report = (yield).get_result()
    if report.when in ['setup', 'call'] and report.failed:
        item.failed = True
