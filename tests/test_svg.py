"""Tests for filer.utils.svg and SVG thumbnailing without an SVG renderer."""

import ast
import pathlib
import unittest
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from easy_thumbnails import VIL
from easy_thumbnails.exceptions import EasyThumbnailsError
from easy_thumbnails.files import get_thumbnailer

from filer.settings import FILER_IMAGE_MODEL
from filer.utils import svg
from filer.utils.loader import load_model


Image = load_model(FILER_IMAGE_MODEL)


SVG_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<svg xmlns="http://www.w3.org/2000/svg" {attrs}>'
    '<rect x="0" y="0" width="10" height="10" fill="red"/>'
    '</svg>'
)


def make_svg(**attrs):
    return SVG_TEMPLATE.format(
        attrs=' '.join(f'{key.replace("_", "")}="{value}"' for key, value in attrs.items())
    ).encode()


class ParseLengthTests(TestCase):
    def test_unitless_and_px(self):
        self.assertEqual(svg.parse_length('120'), 120.0)
        self.assertEqual(svg.parse_length('120px'), 120.0)
        self.assertEqual(svg.parse_length(' 12.5 px '), 12.5)

    def test_absolute_units_convert_to_px(self):
        self.assertAlmostEqual(svg.parse_length('1in'), 96.0)
        self.assertAlmostEqual(svg.parse_length('72pt'), 96.0)
        self.assertAlmostEqual(svg.parse_length('2.54cm'), 96.0)
        self.assertAlmostEqual(svg.parse_length('25.4mm'), 96.0)

    def test_relative_units_are_unresolvable(self):
        for value in ('100%', '2em', '3ex', '', None, 'auto'):
            self.assertIsNone(svg.parse_length(value), value)

    def test_non_finite_lengths_are_rejected(self):
        """``float()`` turns an overflowing exponent into infinity."""
        for value in ('1e999', '-1e999', '1e999pt'):
            self.assertIsNone(svg.parse_length(value), value)


class ParseViewBoxTests(TestCase):
    def test_separators(self):
        self.assertEqual(svg.parse_viewbox('0 0 10 20'), (0.0, 0.0, 10.0, 20.0))
        self.assertEqual(svg.parse_viewbox('0,0,10,20'), (0.0, 0.0, 10.0, 20.0))
        self.assertEqual(svg.parse_viewbox(' -5 -5  10 , 20 '), (-5.0, -5.0, 10.0, 20.0))

    def test_unusable(self):
        for value in ('', None, '0 0 10', '0 0 a b', '0 0 0 10', '0 0 10 -3'):
            self.assertIsNone(svg.parse_viewbox(value), value)

    def test_non_finite_coordinates_are_rejected(self):
        """``float()`` accepts "nan" and "inf", which are not coordinates."""
        for value in ('nan 0 10 10', '0 inf 10 10', '0 0 1e999 10', '0 0 10 -inf'):
            self.assertIsNone(svg.parse_viewbox(value), value)


class LoadTests(TestCase):
    def test_size_from_width_and_height(self):
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        self.assertEqual(image.size, (40.0, 20.0))

    def test_size_from_width_and_height_with_units(self):
        image = svg.load(BytesIO(make_svg(width='1in', height='72pt')))
        self.assertEqual(image.size, (96.0, 96.0))

    def test_size_falls_back_to_viewbox(self):
        image = svg.load(BytesIO(make_svg(width='100%', height='100%', viewBox='0 0 30 15')))
        self.assertEqual(image.size, (30.0, 15.0))

    def test_size_from_viewbox_alone(self):
        image = svg.load(BytesIO(make_svg(viewBox='0 0 30 15')))
        self.assertEqual(image.size, (30.0, 15.0))

    def test_missing_size_is_an_error(self):
        with self.assertRaises(ValueError):
            svg.load(BytesIO(make_svg()))

    def test_malformed_document_is_an_error(self):
        with self.assertRaises(ValueError):
            svg.load(BytesIO(b'<svg><rect></svg>'))

    def test_non_svg_root_is_an_error(self):
        with self.assertRaises(ValueError):
            svg.load(BytesIO(b'<html width="10" height="10"></html>'))

    def test_entity_declarations_are_rejected(self):
        """``xml.etree`` expands internal entities, so "billion laughs" is refused."""
        bomb = (
            b'<!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">'
            b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            b'<desc>&b;</desc></svg>'
        )
        with self.assertRaises(ValueError):
            svg.load(BytesIO(bomb))

    def test_entity_declaration_hidden_in_a_comment_is_rejected(self):
        """A ``]`` inside a DTD comment must not be taken for the subset's end."""
        bomb = (
            b'<!DOCTYPE svg [<!-- ] --><!ENTITY a "aaaaaaaaaa">'
            b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            b'<desc>&b;</desc></svg>'
        )
        with self.assertRaises(ValueError):
            svg.load(BytesIO(bomb))

    def test_entity_declaration_after_a_quoted_bracket_is_rejected(self):
        bomb = (
            b'<!DOCTYPE svg SYSTEM "a]b" [<!ENTITY a "aaaaaaaaaa">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            b'<desc>&a;</desc></svg>'
        )
        with self.assertRaises(ValueError):
            svg.load(BytesIO(bomb))

    def test_entity_declaration_in_another_encoding_is_rejected(self):
        """The check has to see the document the way the parser will."""
        bomb = (
            '<?xml version="1.0" encoding="UTF-16"?>'
            '<!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">]>'
            '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            '<desc>&a;</desc></svg>'
        ).encode('utf-16')
        with self.assertRaises(ValueError):
            svg.load(BytesIO(bomb))

    def test_byte_order_mark_does_not_hide_an_entity_declaration(self):
        bomb = (
            b'\xef\xbb\xbf<!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">]>'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            b'<desc>&a;</desc></svg>'
        )
        with self.assertRaises(ValueError):
            svg.load(BytesIO(bomb))

    def test_non_positive_size_falls_back_to_the_viewbox(self):
        image = svg.load(BytesIO(make_svg(width='0', height='0', viewBox='0 0 8 4')))
        self.assertEqual(image.size, (8.0, 4.0))

    def test_non_positive_size_without_a_viewbox_is_an_error(self):
        for attrs in ({'width': '0', 'height': '0'}, {'width': '-10', 'height': '-5'}):
            with self.assertRaises(ValueError):
                svg.load(BytesIO(make_svg(**attrs)))

    def test_infinite_size_is_an_error(self):
        with self.assertRaises(ValueError):
            svg.load(BytesIO(make_svg(width='1e999', height='10')))

    def test_external_doctype_is_accepted(self):
        """The DTD reference that many authoring tools emit is harmless."""
        document = (
            b'<?xml version="1.0"?>'
            b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
            b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
            b'<svg xmlns="http://www.w3.org/2000/svg" width="50" height="25"/>'
        )
        self.assertEqual(svg.load(BytesIO(document)).size, (50.0, 25.0))

    def test_load_rewinds_the_stream(self):
        handle = BytesIO(make_svg(width='40', height='20'))
        handle.read()
        self.assertEqual(svg.load(handle).size, (40.0, 20.0))

    def test_get_dimensions(self):
        self.assertEqual(
            svg.get_dimensions(BytesIO(make_svg(width='40', height='20'))),
            (40.0, 20.0),
        )


class ResizeAndCropTests(TestCase):
    def serialize(self, image):
        destination = StringIO()
        image.save(destination)
        return ET.fromstring(destination.getvalue())

    def test_resize_sets_width_height_and_viewbox(self):
        image = svg.load(BytesIO(make_svg(width='40', height='20', viewBox='0 0 40 20')))
        resized = image.resize((20, 10))
        self.assertEqual(resized.size, (20.0, 10.0))
        root = self.serialize(resized)
        self.assertEqual(root.get('width'), '20')
        self.assertEqual(root.get('height'), '10')
        self.assertEqual(root.get('viewBox'), '0 0 40 20')

    def test_resize_adds_the_implied_viewbox(self):
        """
        Without a viewBox, changing width and height would only grow the canvas
        and leave the drawing at its original scale.
        """
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        root = self.serialize(image.resize((20, 10)))
        self.assertEqual(root.get('viewBox'), '0 0 40 20')

    def test_resize_keeps_the_contents(self):
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        root = self.serialize(image.resize((20, 10)))
        self.assertEqual(len(root), 1)
        self.assertEqual(root[0].tag, '{http://www.w3.org/2000/svg}rect')

    def test_resize_does_not_touch_the_original(self):
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        image.resize((20, 10))
        self.assertEqual(image.size, (40.0, 20.0))

    def test_crop_maps_pixels_onto_user_units(self):
        # 200x100 px showing a 20x10 user unit viewBox: 1 user unit = 10 px.
        image = svg.load(BytesIO(make_svg(width='200', height='100', viewBox='0 0 20 10')))
        cropped = image.crop((50, 20, 150, 80))
        self.assertEqual(cropped.size, (100.0, 60.0))
        root = self.serialize(cropped)
        self.assertEqual(root.get('width'), '100')
        self.assertEqual(root.get('height'), '60')
        self.assertEqual(root.get('viewBox'), '5 2 10 6')

    def test_crop_respects_the_viewbox_origin(self):
        image = svg.load(BytesIO(make_svg(width='20', height='10', viewBox='-10 -5 20 10')))
        root = self.serialize(image.crop((0, 0, 10, 5)))
        self.assertEqual(root.get('viewBox'), '-10 -5 10 5')

    def test_crop_without_a_box_copies(self):
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        self.assertEqual(image.crop().size, (40.0, 20.0))

    def test_save_keeps_svg_as_the_default_namespace(self):
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        destination = StringIO()
        image.save(destination, format='SVG')
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', destination.getvalue())
        self.assertNotIn('ns0:', destination.getvalue())

    def test_save_rejects_other_formats(self):
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        with self.assertRaises(ValueError):
            image.save(StringIO(), format='PNG')


class SvgThumbnailTests(TestCase):
    """SVG thumbnails are generated without svglib/reportlab being involved."""

    def create_image(self, content=None, name='vector.svg'):
        return Image.objects.create(
            file=SimpleUploadedFile(
                name=name,
                content=content if content is not None else make_svg(
                    width='400', height='200', viewBox='0 0 400 200'),
                content_type='image/svg+xml',
            ),
            original_filename=name,
        )

    def read(self, thumbnail):
        """Read a thumbnail back from storage (the returned file is exhausted)."""
        with thumbnail.storage.open(thumbnail.name) as handle:
            return handle.read()

    def test_dimensions_are_read_on_save(self):
        image = self.create_image()
        self.assertEqual((image.width, image.height), (400.0, 200.0))

    def test_thumbnail_is_a_scaled_svg(self):
        image = self.create_image()
        thumbnail = get_thumbnailer(image).get_thumbnail({'size': (100, 100), 'upscale': False})

        self.assertTrue(thumbnail.name.endswith('.svg'))
        root = ET.fromstring(self.read(thumbnail))
        self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
        # 400x200 scaled to fit into 100x100 keeps the aspect ratio.
        self.assertEqual(root.get('width'), '100')
        self.assertEqual(root.get('height'), '50')
        self.assertEqual(root.get('viewBox'), '0 0 400 200')
        # The vector contents survive untouched.
        self.assertEqual(root[0].tag, '{http://www.w3.org/2000/svg}rect')

    def test_cropped_thumbnail_narrows_the_viewbox(self):
        image = self.create_image()
        thumbnail = get_thumbnailer(image).get_thumbnail({'size': (100, 100), 'crop': True})

        root = ET.fromstring(self.read(thumbnail))
        self.assertEqual(root.get('width'), '100')
        self.assertEqual(root.get('height'), '100')
        # Cropping to a square takes the centre 200 user units of the 400 wide box.
        self.assertEqual(root.get('viewBox'), '100 0 200 200')

    def test_thumbnail_reports_its_dimensions(self):
        image = self.create_image()
        thumbnailer = get_thumbnailer(image)
        options = {'size': (100, 100), 'upscale': False}
        thumbnailer.get_thumbnail(options)

        # A second lookup returns the thumbnail from storage, which has to read
        # its dimensions back from the saved document.
        existing = thumbnailer.get_existing_thumbnail(options)
        self.assertIsNotNone(existing)
        self.assertEqual((existing.width, existing.height), (100.0, 50.0))

    def test_invalid_thumbnail_sizes_are_rejected(self):
        """An SVG is happy to be written at any size, where PIL would refuse."""
        thumbnailer = get_thumbnailer(self.create_image())
        for size in ((0, 0), (-100, 100)):
            with self.assertRaises(EasyThumbnailsError):
                thumbnailer.get_thumbnail({'size': size})

    @unittest.skipUnless(VIL.is_available(), "requires the django-filer[svg] extra")
    def test_relative_size_thumbnails_with_the_optional_renderer(self):
        """
        A document that only the renderer can measure has to thumbnail as well
        as it reports its size - the installation docs promise as much.
        """
        image = self.create_image(
            content=b'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">'
                    b'<rect width="5" height="5"/></svg>',
            name='relative.svg',
        )
        self.assertEqual((image.width, image.height), (100.0, 100.0))
        thumbnail = get_thumbnailer(image).get_thumbnail({'size': (50, 50)})
        self.assertTrue(thumbnail.name.endswith('.svg'))
        self.assertEqual(ET.fromstring(self.read(thumbnail)).tag,
                         '{http://www.w3.org/2000/svg}svg')

    def test_unreadable_svg_leaves_dimensions_unset(self):
        image = self.create_image(content=b'<svg><rect></svg>', name='broken.svg')
        self.assertEqual((image.width, image.height), (0.0, 0.0))


class OptionalDependencyTests(TestCase):
    """
    The SVG renderer is an optional dependency (``django-filer[svg]``).

    Importing it at module level would make filer refuse to start without it, so
    it may only be imported from inside a function.
    """

    OPTIONAL = ('svglib', 'reportlab', 'easy_thumbnails.VIL')

    def import_time_modules(self, tree):
        """Yield the modules a source tree imports when it is imported."""
        def walk(node):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Imports inside a function only run when it is called.
                    continue
                if isinstance(child, ast.Import):
                    yield from (alias.name for alias in child.names)
                elif isinstance(child, ast.ImportFrom) and child.level == 0:
                    yield child.module or ''
                yield from walk(child)

        return walk(tree)

    def test_no_module_level_import_of_the_svg_renderer(self):
        root = pathlib.Path(__file__).resolve().parent.parent / 'filer'
        offenders = []
        for source in sorted(root.rglob('*.py')):
            tree = ast.parse(source.read_text(), filename=str(source))
            for module in self.import_time_modules(tree):
                if module.split('.')[0] in ('svglib', 'reportlab') or module.startswith('easy_thumbnails.VIL'):
                    offenders.append(f'{source.relative_to(root.parent)}: {module}')
        self.assertEqual(offenders, [])
