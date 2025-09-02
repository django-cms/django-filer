import colorsys
import os
import pytest
import random
from collections import namedtuple

from django.conf import settings
from django.core.management import call_command
from django.contrib.admin.sites import site as admin_site
from django.urls import reverse

from finder.models.folder import FolderModel

from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')


class ColorRGBA(namedtuple('ColorRGBA', ['red', 'green', 'blue', 'alpha'])):
    def __new__(cls, red=0, green=0, blue=0, alpha=255):
        return super(ColorRGBA, cls).__new__(cls, red, green, blue, alpha)

    def rotate_hue(self, degrees: float):
        hue, lum, sat = colorsys.rgb_to_hls(self.red, self.blue, self.green)
        hue = (hue + degrees / 360.0) % 1.0
        lum = 255.0 - lum
        red, green, blue = map(int, colorsys.hls_to_rgb(hue, lum, sat))
        return self._replace(red=red, green=green, blue=blue)


@pytest.fixture(autouse=True, scope='session')
def random_image() -> Image:
    background_color = ColorRGBA(red=255, green=255, blue=255)
    image = Image.new('RGB', (4000, 3000), color=background_color)
    drawing = ImageDraw.Draw(image)
    color = ColorRGBA(red=255)
    drawing.rectangle([(10, 10), (130, 130)], fill=color)
    color = color.rotate_hue(25)
    drawing.rectangle([(150, 10), (270, 130)], fill=color)

    # foreground_color = rotate_hue(background_color, 180)
    # font = ImageFont.truetype(Path(__file__).parent / 'fonts/Courier.ttf', 20)
    # drawing.text((10, 90), faker.text(15), fill=foreground_color, font=font)
    image.save(settings.BASE_DIR / 'workdir/assets/demo_image.png')


@pytest.fixture(autouse=True, scope='session')
def create_assets():
    os.makedirs(settings.BASE_DIR / 'workdir/assets', exist_ok=True)
    with open(settings.BASE_DIR / 'workdir/assets/small_file.bin', 'wb') as handle:
        handle.write(random.randbytes(1000))
    with open(settings.BASE_DIR / 'workdir/assets/huge_file.bin', 'wb') as handle:
        handle.write(random.randbytes(100000))
    # image = create_random_image()
    # image.save(settings.BASE_DIR / 'workdir/assets/demo_image.png')


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


@pytest.fixture
def realm(rf, admin_user):
    folder_admin = admin_site.get_model_admin(FolderModel)
    request = rf.get(reverse('admin:finder_foldermodel_changelist'))
    request.user = admin_user
    return folder_admin.get_realm(request)
