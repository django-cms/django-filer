"""
Tests for the crop geometry of `ImageFileModel`. Everything tested here is pure arithmetic on unsaved
model instances — no database, no storage, no image library involved.
"""
import pytest

from finder.contrib.image.models import Gravity, ImageFileModel


def make_image(file_name='picture.png', crop_x=None, crop_y=None, crop_size=None, gravity=Gravity.CENTER):
    return ImageFileModel(
        file_name=file_name,
        crop_x=crop_x,
        crop_y=crop_y,
        crop_size=crop_size,
        gravity=gravity,
    )


class TestCroppedFilename:
    """The cropped file name is the cache key of a sample: whenever it changes, existing samples are
    orphaned and regenerated, so its layout must not change unnoticed."""

    def test_without_crop_area(self):
        image = make_image()
        assert image.get_cropped_filename(180, 180) == 'picture__180x180.png'

    def test_with_crop_area(self):
        image = make_image(crop_x=100, crop_y=50, crop_size=200)
        assert image.get_cropped_filename(400, 200) == 'picture__400x200__100_50_200.png'

    def test_with_crop_area_and_gravity(self):
        image = make_image(crop_x=100, crop_y=50, crop_size=200, gravity=Gravity.NORTHEAST)
        assert image.get_cropped_filename(400, 200) == 'picture__400x200__100_50_200ne.png'

    def test_fractional_values_are_truncated_and_rounded(self):
        """The crop area is truncated towards zero, the output size is rounded."""
        image = make_image(crop_x=1.9, crop_y=2.5, crop_size=3.7)
        assert image.get_cropped_filename(179.6, 180.4) == 'picture__180x180__1_2_3.png'

    def test_keeps_the_suffix_of_the_stored_file(self):
        image = make_image(file_name='picture.with.dots.jpeg')
        assert image.get_cropped_filename(10, 20) == 'picture.with.dots__10x20.jpeg'


class TestCropBoxWithoutCropArea:
    """Without an explicit crop area the largest centered square of the original is used."""

    def test_landscape_original(self):
        image = make_image()
        # a 640x480 original yields the centered 480x480 square
        assert image.compute_crop_box(640, 480, 180, 180) == (80, 0, 560, 480)

    def test_portrait_original(self):
        image = make_image()
        assert image.compute_crop_box(480, 640, 180, 180) == (0, 80, 480, 560)

    def test_square_original(self):
        image = make_image()
        assert image.compute_crop_box(500, 500, 180, 180) == (0, 0, 500, 500)


class TestCropBoxWithCropArea:
    """With an explicit crop area, the box is grown around it until it matches the requested aspect ratio,
    and the gravity decides into which direction it grows."""

    @pytest.mark.parametrize('gravity, expected', [
        (Gravity.CENTER, (0, 0, 400, 400)),
        (Gravity.EAST, (100, 0, 500, 400)),
        (Gravity.WEST, (0, 0, 400, 400)),
        (Gravity.NORTH, (0, 0, 400, 400)),
        (Gravity.SOUTH, (0, 50, 400, 450)),
        (Gravity.NORTHEAST, (100, 0, 500, 400)),
        (Gravity.SOUTHEAST, (100, 50, 500, 450)),
        (Gravity.NORTHWEST, (0, 0, 400, 400)),
        (Gravity.SOUTHWEST, (0, 50, 400, 450)),
    ])
    def test_gravity_moves_the_box(self, gravity, expected):
        # a 200x200 crop area at (100, 50) of a 640x480 original, requested as a 400x400 square
        image = make_image(crop_x=100, crop_y=50, crop_size=200, gravity=gravity)
        assert image.compute_crop_box(640, 480, 400, 400) == expected

    def test_landscape_output_keeps_the_requested_aspect_ratio(self):
        image = make_image(crop_x=100, crop_y=50, crop_size=200)
        min_x, min_y, max_x, max_y = image.compute_crop_box(640, 480, 400, 200)
        assert (min_x, min_y, max_x, max_y) == (0, 50, 400, 250)
        assert (max_x - min_x) / (max_y - min_y) == 2

    def test_portrait_output_keeps_the_requested_aspect_ratio(self):
        image = make_image(crop_x=100, crop_y=50, crop_size=200)
        min_x, min_y, max_x, max_y = image.compute_crop_box(640, 480, 200, 400)
        assert (max_x - min_x) / (max_y - min_y) == 0.5

    def test_box_is_kept_inside_the_original(self):
        """A crop area near the border is shifted back into the image rather than exceeding it."""
        image = make_image(crop_x=600, crop_y=450, crop_size=40, gravity=Gravity.SOUTHEAST)
        min_x, min_y, max_x, max_y = image.compute_crop_box(640, 480, 400, 400)
        assert (min_x, min_y, max_x, max_y) == (240, 80, 640, 480)


class TestCropBoxInvariants:
    """Properties which must hold for every combination, independent of the concrete numbers."""

    @pytest.mark.parametrize('gravity', list(Gravity))
    @pytest.mark.parametrize('crop', [None, (0, 0, 50), (100, 50, 200), (600, 450, 40)])
    @pytest.mark.parametrize('out_size', [(180, 180), (400, 200), (200, 400), (1000, 1000)])
    def test_box_stays_within_the_original_image(self, gravity, crop, out_size):
        crop_x, crop_y, crop_size = crop if crop else (None, None, None)
        image = make_image(crop_x=crop_x, crop_y=crop_y, crop_size=crop_size, gravity=gravity)
        min_x, min_y, max_x, max_y = image.compute_crop_box(640, 480, *out_size)
        assert 0 <= min_x < max_x <= 640
        assert 0 <= min_y < max_y <= 480
