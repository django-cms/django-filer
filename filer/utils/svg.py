"""
Dependency-free handling of the SVG geometry filer needs.

filer only ever asks three things of an SVG: how big it is, a scaled copy and a
cropped copy. All three are attribute changes on the root ``<svg>`` element, so
they need an XML parser rather than an SVG renderer.

``easy_thumbnails.VIL`` answers the same questions by parsing the document with
svglib and re-rendering it through reportlab, which is why
``easy-thumbnails[svg]`` used to be a hard requirement of filer. It is optional
now: it is only consulted as a fallback for documents whose size cannot be read
from the markup itself.
"""

import os
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path


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

# The internal subset of a DTD is the only place where entity declarations can
# appear. ``xml.etree`` expands them, which makes "billion laughs" expansion
# possible, so documents carrying them are rejected. External entities are not
# a concern: expat does not resolve them and reports an undefined entity.
_INTERNAL_SUBSET = re.compile(rb'<!DOCTYPE[^>\[]*\[(.*?)\]', re.DOTALL)


def is_svg(name):
    """Return whether ``name`` looks like the file name of an SVG image."""
    return os.path.splitext(name or '')[1][1:].lower() == 'svg'


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
    return float(number) * factor


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
    if width <= 0 or height <= 0:
        return None
    return x, y, width, height


def _format(number):
    """Render a float the way SVG attributes want it: short, without an exponent."""
    return f'{number:.6f}'.rstrip('0').rstrip('.') or '0'


class SvgImage:
    """
    A minimal, PIL-compatible view on an SVG document.

    It mirrors the subset of ``PIL.Image.Image`` that easy-thumbnails'
    processors use -- and the interface of ``easy_thumbnails.VIL.Image.Image``
    -- so SVG sources can travel through the regular thumbnail pipeline.
    """

    # SVG has no color mode; ``None`` is what VIL reports too.
    mode = None

    def __init__(self, root):
        self.root = root
        viewbox = parse_viewbox(root.get('viewBox'))
        width = parse_length(root.get('width'))
        height = parse_length(root.get('height'))
        if width is None or height is None:
            if viewbox is None:
                raise ValueError(
                    "SVG document declares neither an absolute width and height nor a viewBox"
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

    def save(self, fp, format=None, **params):
        """
        Write the document to ``fp``, which may be a file name, a
        ``pathlib.Path`` or a file object opened in text mode.

        :exception ValueError: If ``format`` is given and is not ``'SVG'``.
        """
        if format is not None and format != 'SVG':
            raise ValueError("Image format is expected to be 'SVG'")
        data = ET.tostring(self.root, encoding='unicode')
        if isinstance(fp, (str, Path)):
            with open(fp, 'w') as handle:
                handle.write(data)
        else:
            fp.write(data)

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

    subset = _INTERNAL_SUBSET.search(content)
    if subset and b'<!ENTITY' in subset.group(1):
        raise ValueError("SVG documents declaring XML entities are not supported")

    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError(f"Cannot parse SVG document: {error}") from error
    if root.tag not in ('svg', f'{{{SVG_NAMESPACE}}}svg'):
        raise ValueError(f"Root element is <{root.tag}>, not <svg>")
    return SvgImage(root)


def _load_with_vil(fp):
    """
    Load ``fp`` through ``easy_thumbnails.VIL``, which renders the document
    with svglib and reportlab. Returns ``None`` if the optional dependency is
    not installed or cannot make sense of the file either.
    """
    try:
        from easy_thumbnails.VIL import Image as VILImage
    except ImportError:
        return None
    if hasattr(fp, 'seek'):
        try:
            fp.seek(0)
        except (OSError, ValueError):
            pass
    try:
        return VILImage.load(fp)
    except Exception:
        return None


def get_dimensions(fp):
    """
    Return the ``(width, height)`` of an SVG document in pixels.

    Documents that do not state their size in absolute units fall back to
    ``easy_thumbnails.VIL`` (``pip install django-filer[svg]``), which can
    derive it by rendering the whole drawing.

    :exception ValueError: If the size cannot be determined at all.
    """
    try:
        return load(fp).size
    except ValueError:
        image = _load_with_vil(fp)
        if image is None:
            raise
        return image.size
