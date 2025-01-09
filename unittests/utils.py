import colorsys
from faker import Faker
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import NewType


ColorRGBA = NewType('ColorRGBA', tuple[int, int, int, int])


def random_color() -> ColorRGBA:
    return *(random.randint(0, 255) for _ in range(3)), 255


def rotate_hue(rgb: ColorRGBA, degrees: float) -> ColorRGBA:
    hue, lum, sat = colorsys.rgb_to_hls(rgb[0], rgb[1], rgb[2])
    hue = (hue + degrees / 360.0) % 1.0
    lum = 255.0 - lum
    return *map(lambda c: int(c), colorsys.hls_to_rgb(hue, lum, sat)), rgb[3]


def create_random_image() -> Image:
    faker = Faker()
    background_color = random_color()
    image = Image.new('RGB', (200, 200), color=background_color)
    drawing = ImageDraw.Draw(image)
    foreground_color = rotate_hue(background_color, 180)
    font = ImageFont.truetype(Path(__file__).parent / 'fonts/Courier.ttf', 20)
    drawing.text((10, 90), faker.text(15), fill=foreground_color, font=font)
    return image
