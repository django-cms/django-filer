"""Tests for filer.thumbnail_processors."""

from django.test import TestCase, override_settings

from filer.thumbnail_processors import (
    normalize_subject_location,
    whitespace,
)

from tests.helpers import create_image


class NormalizeSubjectLocationTests(TestCase):
    """Tests for normalize_subject_location."""

    def test_none_returns_false(self):
        self.assertFalse(normalize_subject_location(None))

    def test_empty_string_returns_false(self):
        self.assertFalse(normalize_subject_location(''))

    def test_falsy_returns_false(self):
        self.assertFalse(normalize_subject_location(False))
        self.assertFalse(normalize_subject_location(0))

    def test_valid_string(self):
        result = normalize_subject_location('400,300')
        self.assertEqual(result, (400, 300))

    def test_valid_string_with_spaces(self):
        result = normalize_subject_location('400, 300')
        self.assertFalse(result)

    def test_valid_tuple(self):
        result = normalize_subject_location((400, 300))
        self.assertEqual(result, (400, 300))

    def test_valid_list(self):
        result = normalize_subject_location([400, 300])
        self.assertEqual(result, (400, 300))

    def test_invalid_string(self):
        result = normalize_subject_location('not-valid')
        self.assertFalse(result)

    def test_invalid_tuple(self):
        result = normalize_subject_location(('a', 'b'))
        self.assertFalse(result)


class WhitespaceProcessorTests(TestCase):
    """Tests for the whitespace thumbnail processor."""

    def test_whitespace_disabled_returns_original(self):
        img = create_image(mode='RGB', size=(200, 100))
        result = whitespace(img, size=(300, 200), whitespace=False)
        self.assertIs(result, img)

    def test_whitespace_larger_source_returns_original(self):
        """Source is larger than target in both dimensions — no whitespace needed."""
        img = create_image(mode='RGB', size=(400, 300))
        result = whitespace(img, size=(200, 200), whitespace=True)
        self.assertIs(result, img)

    def test_whitespace_source_narrower_than_target(self):
        """Source is narrower than target, padding left/right only."""
        img = create_image(mode='RGB', size=(100, 200))
        result = whitespace(img, size=(200, 200), whitespace=True)
        self.assertEqual(result.size, (200, 200))

    def test_whitespace_source_shorter_than_target(self):
        """Source is shorter than target, padding top/bottom only."""
        img = create_image(mode='RGB', size=(200, 100))
        result = whitespace(img, size=(200, 200), whitespace=True)
        self.assertEqual(result.size, (200, 200))

    def test_whitespace_all_around(self):
        """Source fits entirely within target — padding on all sides."""
        img = create_image(mode='RGB', size=(200, 100))
        result = whitespace(img, size=(300, 200), whitespace=True)
        self.assertEqual(result.size, (300, 200))
        self.assertEqual(result.mode, 'RGBA')

    def test_whitespace_exact_fit(self):
        """Source and target are same size — returns original."""
        img = create_image(mode='RGB', size=(200, 100))
        result = whitespace(img, size=(200, 100), whitespace=True)
        self.assertIs(result, img)

    @override_settings(FILER_WHITESPACE_COLOR='#FF0000')
    def test_whitespace_custom_color_from_settings(self):
        img = create_image(mode='RGB', size=(100, 200))
        result = whitespace(img, size=(200, 200), whitespace=True)
        self.assertEqual(result.size, (200, 200))

    def test_whitespace_explicit_color(self):
        img = create_image(mode='RGB', size=(200, 100))
        result = whitespace(img, size=(200, 200), whitespace=True,
                           whitespace_color='#00FF00')
        self.assertEqual(result.size, (200, 200))
