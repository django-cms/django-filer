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

import math
import os
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


class UnresolvableSize(ValueError):
    """
    Raised when a well-formed SVG states no size that can be worked out from the
    markup: a missing or relative width and height, and no viewBox to take the
    size or the aspect ratio from.

    It is the only failure the optional renderer can do anything about, so it is
    the only one :func:`open_image` falls back on. Everything else -- a document
    declaring entities, a root element that is not ``<svg>``, markup that does
    not parse, a width that is not a positive length -- stays rejected whether
    the renderer is installed or not.
    """


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
        # Expected sentinel exception used to stop parsing after the prolog.
        return
    except expat.ExpatError:
        # Malformed: leave the reporting to the parse below, which has the
        # better error message.
        pass


def is_svg(name):
    """Return whether ``name`` looks like the file name of an SVG image."""
    return os.path.splitext(name or '')[1][1:].lower() == 'svg'


def _dimension(value):
    """
    Return ``(length, invalid)`` for a ``width`` or ``height`` attribute.

    ``length`` is the value in pixels, or ``None`` when the attribute does not
    yield one. ``invalid`` tells the two reasons for that apart: markup that is
    simply wrong -- a negative, zero or overflowing length -- as opposed to a
    size that is merely not stated in absolute units, which a renderer could
    still work out.
    """
    if not value or not value.strip():
        # An absent width or height defaults to 100% of the viewport.
        return None, False
    match = _LENGTH.match(value.strip())
    if not match:
        return None, False
    number, unit = match.groups()
    factor = _UNITS_IN_PX.get(unit.lower())
    if factor is None:
        # A relative unit (%, em, ex, ...) has no meaning without a context.
        return None, False
    length = float(number) * factor
    # "1e999" parses as infinity, which overflows as soon as it is used.
    if not math.isfinite(length) or length <= 0:
        return None, True
    return length, False


def parse_length(value):
    """
    Return ``value`` converted to pixels, or ``None`` if it is not a usable
    absolute length. Relative units (``%``, ``em``, ``ex``, ...) cannot be
    resolved without a rendering context, and a width or height has to be a
    positive, finite number to be a size at all.
    """
    return _dimension(value)[0]


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

    It mirrors the subset of ``PIL.Image.Image`` that easy-thumbnails'
    processors use -- and the interface of ``easy_thumbnails.VIL.Image.Image``
    -- so SVG sources can travel through the regular thumbnail pipeline.
    """

    # SVG has no color mode; ``None`` is what VIL reports too.
    mode = None

    def __init__(self, root):
        self.root = root
        viewbox = parse_viewbox(root.get('viewBox'))
        width, width_invalid = _dimension(root.get('width'))
        height, height_invalid = _dimension(root.get('height'))
        if width_invalid or height_invalid:
            # A stated but impossible size is broken markup. The viewBox must
            # not paper over it: the document is saying something wrong, which
            # is different from leaving the size for someone else to work out.
            raise ValueError(
                "SVG document declares a width or height that is not a positive length"
            )
        if viewbox is not None:
            # A viewBox states both a size and an aspect ratio, so a dimension
            # the markup does state is kept and only the missing one is derived
            # from the ratio -- the way a browser sizes an SVG.
            if width is None and height is None:
                width, height = viewbox[2], viewbox[3]
            elif width is None:
                width = height * viewbox[2] / viewbox[3]
            elif height is None:
                height = width * viewbox[3] / viewbox[2]
        if width is None or height is None:
            raise UnresolvableSize(
                "SVG document states no absolute width and height and has no viewBox"
            )
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
                # Some file-like objects are not seekable; continue reading
                # from the current position to preserve compatibility.
                _ = None
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
            # Best-effort rewind only; some file-like objects are not seekable.
            # Continue and let VIL try to load from the current stream position.
            pass
    try:
        image = VILImage.load(fp)
    except Exception:
        return None
    if image is None:
        return None
    try:
        width, height = (float(value) for value in image.size)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(width) or not math.isfinite(height) or width <= 0 or height <= 0:
        # The renderer reports a zero or partial size for documents it cannot
        # size either, which is no more usable than no answer at all.
        return None
    return image


def open_image(fp):
    """
    Return an image for ``fp``: an :class:`SvgImage`, or a
    ``easy_thumbnails.VIL`` one for documents that do not state their size in
    absolute units and can only be measured by rendering the whole drawing.
    The two share the interface the thumbnail pipeline needs.

    The renderer is the optional ``django-filer[svg]`` extra; without it such a
    document cannot be measured at all. It is only asked about
    :class:`UnresolvableSize`: a document filer rejects stays rejected either
    way, so installing the extra can never weaken a check.

    :exception ValueError: If no image can be opened.
    """
    try:
        return load(fp)
    except UnresolvableSize:
        image = _load_with_vil(fp)
        if image is None:
            raise
        return image


def get_dimensions(fp):
    """
    Return the ``(width, height)`` of an SVG document in pixels.

    :exception ValueError: If the size cannot be determined.
    """
    return open_image(fp).size
