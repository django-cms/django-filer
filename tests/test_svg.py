"""Tests for filer.utils.svg and SVG thumbnailing without an SVG renderer."""

import ast
import pathlib
import unittest
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from easy_thumbnails import VIL
from easy_thumbnails.exceptions import EasyThumbnailsError, InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer

from filer.settings import FILER_IMAGE_MODEL
from filer.utils import svg
from filer.utils.filer_easy_thumbnails import svg_source_generator
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

    def test_stated_width_is_kept_and_height_follows_the_viewbox_ratio(self):
        """
        A viewBox states an aspect ratio as well as a size, so a width the
        markup does give must not be thrown away for the viewBox's own width.
        """
        image = svg.load(BytesIO(make_svg(width='200', viewBox='0 0 100 50')))
        self.assertEqual(image.size, (200.0, 100.0))

    def test_stated_height_is_kept_and_width_follows_the_viewbox_ratio(self):
        image = svg.load(BytesIO(make_svg(height='200', viewBox='0 0 100 50')))
        self.assertEqual(image.size, (400.0, 200.0))

    def test_both_stated_dimensions_win_over_the_viewbox(self):
        image = svg.load(BytesIO(make_svg(width='200', height='33', viewBox='0 0 100 50')))
        self.assertEqual(image.size, (200.0, 33.0))

    def test_size_from_viewbox_alone(self):
        image = svg.load(BytesIO(make_svg(viewBox='0 0 30 15')))
        self.assertEqual(image.size, (30.0, 15.0))

    def test_missing_size_is_unresolvable(self):
        """Only a renderer can size a document that states no size at all."""
        with self.assertRaises(svg.UnresolvableSize):
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

    def test_the_viewbox_does_not_rescue_an_impossible_size(self):
        """
        Inference fills in what the markup leaves out; it must not overwrite
        what the markup gets wrong.
        """
        for attrs in ({'width': '0', 'height': '0'},
                      {'width': '-10', 'height': '20'},
                      {'width': '1e999', 'height': '20'}):
            with self.assertRaises(ValueError) as caught:
                svg.load(BytesIO(make_svg(viewBox='0 0 100 50', **attrs)))
            self.assertNotIsInstance(caught.exception, svg.UnresolvableSize)

    def test_non_positive_size_without_a_viewbox_is_an_error(self):
        """A stated but impossible size is wrong markup, not a missing size."""
        for attrs in ({'width': '0', 'height': '0'}, {'width': '-10', 'height': '-5'}):
            with self.assertRaises(ValueError) as caught:
                svg.load(BytesIO(make_svg(**attrs)))
            self.assertNotIsInstance(caught.exception, svg.UnresolvableSize)

    def test_infinite_size_is_an_error(self):
        with self.assertRaises(ValueError) as caught:
            svg.load(BytesIO(make_svg(width='1e999', height='10')))
        self.assertNotIsInstance(caught.exception, svg.UnresolvableSize)

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

    def test_crop_with_a_degenerate_box_copies(self):
        """A box with no area leaves the image at its current geometry."""
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        for box in ((10, 10, 10, 10), (30, 0, 10, 20)):
            cropped = image.crop(box)
            self.assertEqual(cropped.size, (40.0, 20.0), box)

    def test_filter_is_a_no_op(self):
        """The ``detail`` and ``sharpen`` processors do not apply to vectors."""
        image = svg.load(BytesIO(make_svg(width='40', height='20')))
        self.assertIs(image.filter('anything'), image)

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
        # What the renderer makes of "100%" is its business and varies by
        # version; that it yields a usable size at all is filer's.
        self.assertGreater(image.width, 0)
        self.assertGreater(image.height, 0)
        thumbnail = get_thumbnailer(image).get_thumbnail({'size': (50, 50)})
        self.assertTrue(thumbnail.name.endswith('.svg'))
        self.assertEqual(ET.fromstring(self.read(thumbnail)).tag,
                         '{http://www.w3.org/2000/svg}svg')

    def test_source_generator_without_a_source(self):
        """easy-thumbnails passes ``None`` when it cannot open the file."""
        self.assertIsNone(svg_source_generator(None))

    def test_unopenable_svg_reports_an_invalid_image_format(self):
        """
        The ``{% thumbnail %}`` tag asks the source generators for silence, so a
        file named ``.svg`` that is not SVG surfaces here rather than earlier.
        """
        image = self.create_image(content=b'this is not markup', name='notreally.svg')
        with self.assertRaises(InvalidImageFormatError):
            get_thumbnailer(image).get_thumbnail(
                {'size': (100, 100)}, silent_template_exception=True)

    def test_unparseable_thumbnail_size_is_rejected(self):
        """A size with no numbers in it leaves nothing to scale to."""
        thumbnailer = get_thumbnailer(self.create_image())
        with self.assertRaises(EasyThumbnailsError):
            thumbnailer.get_thumbnail({'size': ('wide', None)})

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


class ImageSizeGuardTests(TestCase):
    """
    ``BaseImage.clean()`` measures every image it can against
    ``FILER_MAX_IMAGE_PIXELS``, vector images included.

    Only images whose dimensions cannot be read are treated by type: for a
    raster image that is itself the signature of a decompression bomb, since
    Pillow reports no size for one, while a vector image has no pixel count to
    compare against.
    """

    def unmeasurable_image(self, name, mime_type):
        image = Image(
            file=SimpleUploadedFile(name=name, content=b'...', content_type=mime_type),
            original_filename=name,
            mime_type=mime_type,
        )
        image._width, image._height = None, None
        return image

    def test_vector_image_without_dimensions_is_allowed(self):
        self.unmeasurable_image('vector.svg', 'image/svg+xml').clean()

    def test_oversized_vector_image_is_rejected(self):
        """An SVG that does state its size is measured like any other image."""
        image = self.unmeasurable_image('huge.svg', 'image/svg+xml')
        image._width, image._height = 30000, 30000
        with self.assertRaises(ValidationError) as caught:
            image.clean()
        self.assertEqual(caught.exception.code, 'image_size')

    def test_raster_image_without_dimensions_is_rejected(self):
        image = self.unmeasurable_image('photo.jpg', 'image/jpeg')
        with self.assertRaises(ValidationError) as caught:
            image.clean()
        self.assertEqual(caught.exception.code, 'image_size')


@unittest.skipUnless(VIL.is_available(), "requires the django-filer[svg] extra")
class RendererFallbackTests(TestCase):
    """
    Installing the optional renderer must never weaken a check.

    ``open_image()`` falls back to it for one failure only - a document whose
    size cannot be worked out from the markup. Anything filer rejects has to
    stay rejected, or the renderer would quietly launder documents past the
    entity, root-element and geometry checks.
    """

    def open(self, content):
        return svg.open_image(
            SimpleUploadedFile('doc.svg', content, content_type='image/svg+xml'))

    def test_entity_declarations_are_not_laundered(self):
        with self.assertRaises(ValueError):
            self.open(
                b'<!DOCTYPE svg [<!ENTITY a "aaaaaaaaaa">]>'
                b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
                b'<desc>&a;</desc></svg>')

    def test_a_non_svg_root_is_not_laundered(self):
        with self.assertRaises(ValueError):
            self.open(b'<html width="10" height="10"></html>')

    def test_malformed_markup_is_not_laundered(self):
        with self.assertRaises(ValueError):
            self.open(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
                      b'<rect></svg>')

    def test_impossible_dimensions_are_not_laundered(self):
        for attrs in (b'width="-10" height="10"', b'width="0" height="10"',
                      b'width="1e999" height="10"'):
            with self.assertRaises(ValueError):
                self.open(b'<svg xmlns="http://www.w3.org/2000/svg" ' + attrs + b'/>')

    def test_a_partial_renderer_size_is_not_accepted(self):
        """
        The renderer answers ``(200, 0)`` for a document stating only a width,
        and ``(0, 0)`` for one stating nothing. Neither is a size.
        """
        for attrs in (b'width="200"', b''):
            with self.assertRaises(svg.UnresolvableSize):
                self.open(b'<svg xmlns="http://www.w3.org/2000/svg" ' + attrs +
                          b'><rect width="5" height="5"/></svg>')

    def test_an_unresolvable_size_is_what_the_renderer_is_for(self):
        image = self.open(
            b'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">'
            b'<rect width="5" height="5"/></svg>')
        self.assertIsNotNone(image)


@unittest.skipIf(VIL.is_available(), "covers a default install, without the extra")
class WithoutRendererTests(TestCase):
    """
    What a plain ``pip install django-filer`` makes of a document only the
    optional renderer could measure. The mirror image of
    :class:`RendererFallbackTests`, so that both installations are covered.
    """

    RELATIVE = (b'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">'
                b'<rect width="5" height="5"/></svg>')

    def test_open_image_reports_the_size_as_unresolvable(self):
        with self.assertRaises(svg.UnresolvableSize):
            svg.open_image(SimpleUploadedFile(
                'relative.svg', self.RELATIVE, content_type='image/svg+xml'))

    def test_dimensions_stay_unset(self):
        """The admin falls back to a generic icon rather than failing."""
        image = Image.objects.create(
            file=SimpleUploadedFile(
                'relative.svg', self.RELATIVE, content_type='image/svg+xml'),
            original_filename='relative.svg',
        )
        self.assertEqual((image.width, image.height), (0.0, 0.0))
