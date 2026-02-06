import colorsys
import random
from collections import namedtuple

from django.core.management.base import BaseCommand
from django.conf import settings

from PIL import Image, ImageDraw


class ColorRGBA(namedtuple('ColorRGBA', ['red', 'green', 'blue', 'alpha'])):
    def __new__(cls, red=0, green=0, blue=0, alpha=255):
        return super(ColorRGBA, cls).__new__(cls, red, green, blue, alpha)

    def set_lum(self, lum: float):
        hue, _, sat = colorsys.rgb_to_hls(self.red / 255.0, self.green / 255.0, self.blue / 255.0)
        red, green, blue = [int(c * 255) for c in colorsys.hls_to_rgb(hue, lum / 255.0, sat)]
        return self._replace(red=red, green=green, blue=blue)

    def rotate_hue(self, degrees: float):
        hue, lum, sat = colorsys.rgb_to_hls(self.red / 255.0, self.green / 255.0, self.blue / 255.0)
        hue = (hue + degrees / 360.0) % 1.0
        red, green, blue = [int(c * 255) for c in colorsys.hls_to_rgb(hue, lum, sat)]
        return self._replace(red=red, green=green, blue=blue)


class Command(BaseCommand):
    help = "Create demo image."

    def handle(self, verbosity, *args, **options):
        self.verbosity = verbosity
        self.create_image(1210, 810, 10)

    def create_image(self, width, height, gap):
        border_color = ColorRGBA(red=0, green=0, blue=0)
        background_color = ColorRGBA(red=255, green=255, blue=255)
        image = Image.new('RGB', (width, height), color=border_color)
        drawing = ImageDraw.Draw(image)
        drawing.rectangle([(gap, gap), (width - gap, height - gap)], fill=background_color)

        line_color = ColorRGBA(red=30, green=150, blue=10)
        for y in range(2 * gap, height - gap, 2 * gap):
            color = line_color = line_color.set_lum(random.gauss(128, 50))
            for x in range(2 * gap, width - gap, 2 * gap):
                color = color.rotate_hue(random.randint(-15, 25))
                drawing.rectangle([(x, y), (x + gap, y + gap)], fill=color)

        # color = color.rotate_hue(25)
        # drawing.rectangle([(150, 10), (270, 130)], fill=color)

        # foreground_color = rotate_hue(background_color, 180)
        # font = ImageFont.truetype(Path(__file__).parent / 'fonts/Courier.ttf', 20)
        # drawing.text((10, 90), faker.text(15), fill=foreground_color, font=font)
        image.save(settings.BASE_DIR / 'workdir/assets/demo_image.png')
