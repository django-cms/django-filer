"""
Unit tests for the two opt-in SVG validators of `finder.contrib.image.svg.validators`.

`sanitize_svg()`, the validator registered for `image/svg+xml` by default, is covered by
`test_validation.py` along with the rest of the validator machinery. `svg_validator()` and
`xml_validator()` are the rejecting variants a project may register instead; they are still
documented in `docs/how-to/validate-uploads.rst` and used by `demoapp.settings`, hence they
are tested here.
"""

import sys

from importlib.util import find_spec
from io import BytesIO

import pytest

from finder.contrib.image.svg.validators import svg_validator, xml_validator


VALID_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    b'<rect width="10" height="10"/>'
    b'</svg>'
)
MALFORMED_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect></svg>'
ENTITY_SVG = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    b'<svg xmlns="http://www.w3.org/2000/svg">&xxe;</svg>'
)

requires_py_svg_hush = pytest.mark.skipif(
    find_spec('py_svg_hush') is None,
    reason="The optional package py_svg_hush is not installed.",
)
requires_defusedxml = pytest.mark.skipif(
    find_spec('defusedxml') is None,
    reason="The optional package defusedxml is not installed.",
)


class TestSvgValidator:
    """Rejects an SVG which py-svg-hush cannot parse."""

    def test_a_valid_svg_is_accepted(self):
        assert svg_validator('valid.svg', BytesIO(VALID_SVG), None, 'image/svg+xml') is None

    @requires_py_svg_hush
    def test_unparsable_content_is_rejected(self):
        with pytest.raises(ValueError, match="Invalid or malicious SVG in “broken.svg”"):
            svg_validator('broken.svg', BytesIO(b'this is not XML at all <<<'), None, 'image/svg+xml')

    def test_it_accepts_everything_without_py_svg_hush(self, monkeypatch):
        """
        Unlike `sanitize_svg()`, this validator fails open: it only rejects what the
        optional dependency rejects, so without it there is nothing left to reject.
        """
        monkeypatch.setitem(sys.modules, 'py_svg_hush', None)
        assert svg_validator('broken.svg', BytesIO(b'not XML <<<'), None, 'image/svg+xml') is None


class TestXmlValidator:
    """Rejects XML which defusedxml refuses to parse: XXE, billion laughs, malformed input."""

    def test_a_valid_svg_is_accepted(self):
        assert xml_validator('valid.svg', BytesIO(VALID_SVG), None, 'image/svg+xml') is None

    @requires_defusedxml
    def test_malformed_xml_is_rejected(self):
        with pytest.raises(ValueError, match="Invalid or malicious SVG in “broken.svg”"):
            xml_validator('broken.svg', BytesIO(MALFORMED_SVG), None, 'image/svg+xml')

    @requires_defusedxml
    def test_entity_declarations_are_rejected(self):
        """Entity declarations are the vector for XXE and billion laughs attacks."""
        with pytest.raises(ValueError):
            xml_validator('xxe.svg', BytesIO(ENTITY_SVG), None, 'image/svg+xml')

    def test_it_accepts_everything_without_defusedxml(self, monkeypatch):
        monkeypatch.setitem(sys.modules, 'defusedxml.ElementTree', None)
        assert xml_validator('broken.svg', BytesIO(MALFORMED_SVG), None, 'image/svg+xml') is None
