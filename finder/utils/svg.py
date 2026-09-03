"""
Dependency-free handling of the SVG geometry finder needs.

finder only ever asks three things of an SVG: how big it is, a cropped copy and
a scaled copy. All three are attribute changes on the root ``<svg>`` element, so
they need an XML parser rather than an SVG renderer.

Before this module, ``finder.contrib.image.svg`` answered the same questions by
parsing the document with svglib and re-drawing it onto a reportlab canvas,
which is why ``django-finder[svg]`` used to install roughly 14 MB of renderer.
Rewriting the root element instead keeps the original vector data intact rather
than replacing it with a renderer's interpretation of it.

Ported from ``filer.utils.svg`` (django-filer#1624). The API is kept
deliberately close to it, minus the svglib fallback for documents that state
their size only in relative units: finder falls back to a generic icon for
those (see ``ImageFileModel.fallback_thumbnail_url``) instead of pulling in a
renderer to measure them.
"""

import math
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from xml.parsers import expat


SVG_NAMESPACE = 'http://www.w3.org/2000/svg'
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'

# Serialize with the customary prefixes instead of ET's generated "ns0:" ones.
# The namespace URI is what matters, but renderers have been known to key on the
# literal ``xlink:`` prefix.
ET.register_namespace('', SVG_NAMESPACE)
ET.register_namespace('xlink', XLINK_NAMESPACE)

# CSS absolute length units expressed in pixels.
# See https://www.w3.org/TR/css-values-3/#absolute-lengths
_UNITS_IN_PX = {
    '': 1.0,
    'px': 1.0,
    'pt': 96 / 72,
    'pc': 16.0,
    'in': 96.0,
    'cm': 96 / 2.54,
    'mm': 96 / 25.4,
    'q': 96 / 101.6,
}

_LENGTH = re.compile(r'^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-z%]*)$')


class _EntityDeclaration(Exception):
    """Raised out of the expat handler when the document declares an entity."""


class _PrologParsed(Exception):
    """Raised out of the expat handler once the root element starts."""


def reject_entity_declarations(content):
    """
    Refuse documents that declare XML entities.

    ``xml.etree`` expands internal entities, so a handful of nested declarations
    expand to gigabytes ("billion laughs"). Entities can only be declared in a
    DTD, which expat reports before the root element starts, so this reads no
    further than the prolog. Letting expat do it rather than matching the markup
    means comments, quoting and the document's encoding are all handled by the
    same parser that will parse it for real.

    External entities need no handling: expat does not resolve them and does not
    fetch external DTD subsets, it reports an undefined entity instead.

    :exception ValueError: If the document declares an entity.
    """
    parser = expat.ParserCreate()

    def entity_declared(*args, **kwargs):
        raise _EntityDeclaration

    def root_element_started(*args, **kwargs):
        raise _PrologParsed

    parser.EntityDeclHandler = entity_declared
    parser.UnparsedEntityDeclHandler = entity_declared
    parser.StartElementHandler = root_element_started
    try:
        parser.Parse(content, True)
    except _EntityDeclaration:
        raise ValueError("SVG documents declaring XML entities are not supported") from None
    except _PrologParsed:
        pass
    except expat.ExpatError:
        # Malformed: leave the reporting to the parse below, which has the
        # better error message.
        pass


def parse_length(value):
    """
    Return ``value`` converted to pixels, or ``None`` if it is not an absolute
    length. Relative units (``%``, ``em``, ``ex``, ...) cannot be resolved
    without a rendering context; the ``viewBox`` is the better source then.
    """
    if not value:
        return None
    match = _LENGTH.match(value.strip())
    if not match:
        return None
    number, unit = match.groups()
    try:
        factor = _UNITS_IN_PX[unit.lower()]
    except KeyError:
        return None
    length = float(number) * factor
    # "1e999" parses as infinity, which overflows as soon as it is used.
    return length if math.isfinite(length) else None


def parse_viewbox(value):
    """
    Return the ``viewBox`` attribute as an ``(x, y, width, height)`` tuple of
    user units, or ``None`` if it is missing or unusable.
    """
    if not value:
        return None
    parts = re.split(r'[\s,]+', value.strip())
    if len(parts) != 4:
        return None
    try:
        x, y, width, height = (float(part) for part in parts)
    except ValueError:
        return None
    # float() happily accepts "nan" and "inf", which are not coordinates.
    if not all(math.isfinite(value) for value in (x, y, width, height)):
        return None
    if width <= 0 or height <= 0:
        return None
    return x, y, width, height


def _format(number):
    """Render a float the way SVG attributes want it: short, without an exponent."""
    return f'{number:.6f}'.rstrip('0').rstrip('.') or '0'


class SvgImage:
    """
    A minimal, PIL-compatible view on an SVG document.

    It mirrors the subset of ``PIL.Image.Image`` that ``ImageFileModel.crop()``
    uses, so that the SVG and the PIL backend can be written the same way.
    """

    # SVG has no color mode; ``None`` is what easy-thumbnails' VIL reports too.
    mode = None
    format = 'SVG'

    def __init__(self, root):
        self.root = root
        viewbox = parse_viewbox(root.get('viewBox'))
        width = parse_length(root.get('width'))
        height = parse_length(root.get('height'))
        if width is None or height is None or width <= 0 or height <= 0:
            # A size that is missing, relative or not a positive length at all
            # leaves the viewBox as the only thing left to measure.
            if viewbox is None:
                raise ValueError(
                    "SVG document declares no usable width and height and no viewBox"
                )
            width, height = viewbox[2], viewbox[3]
        if viewbox is None:
            # Without a viewBox, changing width and height resizes the canvas
            # but not its contents. Fall back to the implied one.
            viewbox = (0.0, 0.0, width, height)
        self.width = float(width)
        self.height = float(height)
        self.viewbox = viewbox

    @property
    def size(self):
        return self.width, self.height

    def getbbox(self):
        """
        Return the bounding box as a 4-tuple of the left, upper, right and
        lower pixel coordinate.
        """
        return 0.0, 0.0, self.width, self.height

    def resize(self, size, **kwargs):
        """Return a copy scaled to ``size``, a ``(width, height)`` 2-tuple."""
        width, height = (float(value) for value in size)
        copy = SvgImage(deepcopy(self.root))
        copy._set_geometry(width, height, self.viewbox)
        return copy

    def thumbnail(self, size, **kwargs):
        """
        Scale this image down in place to fit inside ``size``, preserving its
        aspect ratio.

        Mirrors ``PIL.Image.Image.thumbnail()``, including its refusal to
        enlarge: a document already smaller than ``size`` is left alone, so the
        two image backends produce thumbnails of the same dimensions.
        """
        width, height = (float(value) for value in size)
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid thumbnail size ({size[0]}x{size[1]})")
        if self.width <= width and self.height <= height:
            return
        scale = min(width / self.width, height / self.height)
        self._set_geometry(self.width * scale, self.height * scale, self.viewbox)

    def crop(self, box=None):
        """
        Return a rectangular region of this image as a copy.

        ``box`` is a ``(left, upper, right, lower)`` 4-tuple in pixels, which
        is mapped onto the user coordinate system of the current ``viewBox``.
        """
        copy = SvgImage(deepcopy(self.root))
        if not box:
            return copy
        left, upper, right, lower = (float(value) for value in box)
        width, height = right - left, lower - upper
        if width <= 0 or height <= 0:
            return copy
        view_x, view_y, view_width, view_height = self.viewbox
        scale_x = view_width / self.width if self.width else 1.0
        scale_y = view_height / self.height if self.height else 1.0
        copy._set_geometry(width, height, (
            view_x + left * scale_x,
            view_y + upper * scale_y,
            width * scale_x,
            height * scale_y,
        ))
        return copy

    def convert(self, *args, **kwargs):
        """Does nothing, just for compatibility with PIL."""
        return self

    def filter(self, *args, **kwargs):
        """Does nothing, just for compatibility with PIL."""
        return self

    def tobytes(self):
        """Return the document serialized as UTF-8 encoded XML."""
        return ET.tostring(self.root, encoding='utf-8', xml_declaration=True)

    def save(self, fp, format=None, **params):
        """
        Write the document to ``fp``, which may be a file name, a
        ``pathlib.Path`` or a file object opened in either binary or text mode.

        :exception ValueError: If ``format`` is given and is not ``'SVG'``.
        """
        if format is not None and format != 'SVG':
            raise ValueError("Image format is expected to be 'SVG'")
        data = self.tobytes()
        if isinstance(fp, (str, Path)):
            with open(fp, 'wb') as handle:
                handle.write(data)
            return
        try:
            fp.write(data)
        except TypeError:
            fp.write(data.decode())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def _set_geometry(self, width, height, viewbox):
        self.width, self.height, self.viewbox = width, height, viewbox
        self.root.set('width', _format(width))
        self.root.set('height', _format(height))
        self.root.set('viewBox', ' '.join(_format(value) for value in viewbox))


def load(fp):
    """
    Return an :class:`SvgImage` for ``fp``, which may be a file name, a
    ``pathlib.Path``, a Django ``File`` or any object with a ``read()`` method.

    :exception ValueError: If the document is not parseable SVG or does not
        declare a size.
    """
    if hasattr(fp, 'read'):
        if hasattr(fp, 'seek'):
            try:
                fp.seek(0)
            except (OSError, ValueError):
                pass
        content = fp.read()
    else:
        with open(fp, 'rb') as handle:
            content = handle.read()
    if isinstance(content, str):
        content = content.encode()

    reject_entity_declarations(content)

    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError(f"Cannot parse SVG document: {error}") from error
    if root.tag not in ('svg', f'{{{SVG_NAMESPACE}}}svg'):
        raise ValueError(f"Root element is <{root.tag}>, not <svg>")
    return SvgImage(root)


def get_dimensions(fp):
    """
    Return the ``(width, height)`` of an SVG document in pixels.

    :exception ValueError: If the size cannot be determined.
    """
    return load(fp).size
