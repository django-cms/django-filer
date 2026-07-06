"""Tests for filer.templatetags.filer_image_tags."""

from django.test import TestCase

from filer.templatetags.filer_image_tags import (
    _recalculate_size,
    _resize,
    divide_x_by,
    divide_xy_by,
    divide_y_by,
    extra_padding_x,
    extra_padding_x_keep_ratio,
    extra_padding_y,
    extra_padding_y_keep_ratio,
    get_css_position,
    percentage,
)


class PercentageTests(TestCase):
    def test_percentage_basic(self):
        self.assertEqual(percentage(50, 200), 25.0)

    def test_percentage_zero_part(self):
        self.assertEqual(percentage(0, 200), 0.0)

    def test_percentage_full(self):
        self.assertEqual(percentage(200, 200), 100.0)

    def test_percentage_float(self):
        self.assertAlmostEqual(percentage(1, 3), 100.0 / 3.0)

    def test_percentage_zero_total(self):
        with self.assertRaises(ZeroDivisionError):
            percentage(10, 0)

    def test_percentage_zero_total_zero_part(self):
        with self.assertRaises(ZeroDivisionError):
            percentage(0, 0)


class RecalculateSizeTests(TestCase):
    """Tests for _recalculate_size."""

    def test_basic_no_divisor_no_padding_no_aspect(self):
        result = _recalculate_size(size=(800, 600), index=0)
        self.assertEqual(result, (800, 600))

    def test_basic_no_divisor_no_padding_no_aspect_index_1(self):
        result = _recalculate_size(size=(800, 600), index=1)
        self.assertEqual(result, (800, 600))

    def test_with_divisor_index_0(self):
        result = _recalculate_size(size=(800, 600), index=0, divisor=2)
        self.assertEqual(result, (400, 600))

    def test_with_divisor_index_1(self):
        result = _recalculate_size(size=(800, 600), index=1, divisor=2)
        self.assertEqual(result, (800, 300))

    def test_with_padding_index_0(self):
        result = _recalculate_size(size=(800, 600), index=0, padding=50)
        self.assertEqual(result, (750, 600))

    def test_with_padding_index_1(self):
        result = _recalculate_size(size=(800, 600), index=1, padding=50)
        self.assertEqual(result, (800, 550))

    def test_keep_aspect_ratio_index_0(self):
        result = _recalculate_size(size=(800, 600), index=0, divisor=2, keep_aspect_ratio=True)
        self.assertEqual(result, (400, 300))

    def test_keep_aspect_ratio_index_1(self):
        result = _recalculate_size(size=(800, 600), index=1, divisor=2, keep_aspect_ratio=True)
        self.assertEqual(result, (400, 300))

    def test_keep_aspect_ratio_with_padding(self):
        result = _recalculate_size(size=(800, 600), index=0, padding=100, keep_aspect_ratio=True)
        self.assertEqual(result, (700, 525))


class ResizeTests(TestCase):
    """Tests for _resize."""

    def test_string_size(self):
        result = _resize("800x600", index=0, divisor=2)
        self.assertEqual(result, (400, 600))

    def test_string_size_invalid(self):
        result = _resize("not-a-size", index=0, divisor=2)
        self.assertEqual(result, "not-a-size")

    def test_tuple_size(self):
        result = _resize((800, 600), index=0, divisor=2)
        self.assertEqual(result, (400, 600))

    def test_tuple_size_invalid(self):
        result = _resize(("a", "b"), index=0, divisor=2)
        self.assertEqual(result, ("a", "b"))

    def test_invalid_padding(self):
        result = _resize((800, 600), index=0, padding="bad")
        self.assertEqual(result, (800, 600))

    def test_invalid_divisor(self):
        result = _resize((800, 600), index=0, divisor="bad")
        self.assertEqual(result, (800, 600))

    def test_with_divisor_and_keep_aspect_ratio(self):
        result = _resize((800, 600), index=1, divisor=2, keep_aspect_ratio=True)
        self.assertEqual(result, (400, 300))


class ExtraPaddingXTests(TestCase):
    """Tests for extra_padding_x template filter."""

    def test_basic(self):
        result = extra_padding_x("800x600", 100)
        self.assertEqual(result, (700, 600))

    def test_tuple_input(self):
        result = extra_padding_x((800, 600), 100)
        self.assertEqual(result, (700, 600))


class ExtraPaddingXKeepRatioTests(TestCase):
    """Tests for extra_padding_x_keep_ratio template filter."""

    def test_basic(self):
        result = extra_padding_x_keep_ratio("800x600", 100)
        self.assertEqual(result, (700, 525))


class ExtraPaddingYTests(TestCase):
    """Tests for extra_padding_y template filter."""

    def test_basic(self):
        result = extra_padding_y("800x600", 100)
        self.assertEqual(result, (800, 500))

    def test_tuple_input(self):
        result = extra_padding_y((800, 600), 100)
        self.assertEqual(result, (800, 500))


class ExtraPaddingYKeepRatioTests(TestCase):
    """Tests for extra_padding_y_keep_ratio template filter."""

    def test_basic(self):
        result = extra_padding_y_keep_ratio("800x600", 100)
        self.assertEqual(result, (666, 500))


class DivideXByTests(TestCase):
    """Tests for divide_x_by template filter."""

    def test_basic(self):
        result = divide_x_by("800x600", 2)
        self.assertEqual(result, (400, 600))

    def test_tuple_input(self):
        result = divide_x_by((800, 600), 2)
        self.assertEqual(result, (400, 600))


class DivideYByTests(TestCase):
    """Tests for divide_y_by template filter."""

    def test_basic(self):
        result = divide_y_by("800x600", 2)
        self.assertEqual(result, (800, 300))

    def test_tuple_input(self):
        result = divide_y_by((800, 600), 2)
        self.assertEqual(result, (800, 300))


class DivideXYByTests(TestCase):
    """Tests for divide_xy_by template filter."""

    def test_basic(self):
        result = divide_xy_by("800x600", 2)
        self.assertEqual(result, (400, 300))

    def test_tuple_input(self):
        result = divide_xy_by((800, 600), 2)
        self.assertEqual(result, (400, 300))


class GetCssPositionTests(TestCase):
    """Tests for get_css_position template filter."""

    def test_no_image(self):
        result = get_css_position(None)
        self.assertEqual(result, '50% 50%')

    def test_no_subject_location(self):
        class FakeImage:
            subject_location = None
            width = 800
            height = 600

        result = get_css_position(FakeImage())
        self.assertEqual(result, '50% 50%')

    def test_with_subject_location(self):
        class FakeImage:
            subject_location = '400,300'
            width = 800
            height = 600

        result = get_css_position(FakeImage())
        self.assertEqual(result, '50.0% 50.0%')

    def test_with_subject_location_offset(self):
        class FakeImage:
            subject_location = '200,150'
            width = 800
            height = 600

        result = get_css_position(FakeImage())
        self.assertEqual(result, '25.0% 25.0%')
