"""
Tests for `PILImageModel.store_and_save`.

Its body is wrapped in `except Exception: pass`, so none of this can fail loudly: if the image handling
breaks, files are simply stored unprocessed and with zeroed dimensions. These tests are the only signal.
"""
import pytest

from io import BytesIO

from PIL import ExifTags, Image

from django.core.files.uploadedfile import SimpleUploadedFile

from finder.contrib.image.pil.models import PILImageModel


def upload_image(ambit, owner, image, name='picture.png', image_format='PNG', **save_kwargs):
    buffer = BytesIO()
    image.save(buffer, format=image_format, **save_kwargs)
    mime_type = f'image/{image_format.lower()}'
    uploaded_file = SimpleUploadedFile(name, buffer.getvalue(), content_type=mime_type)
    return PILImageModel.objects.create_from_upload(
        ambit, uploaded_file, folder=ambit.root_folder, owner=owner, mime_type=mime_type,
    )


def stored_image(ambit, file_obj):
    with ambit.original_storage.open(file_obj.file_path, 'rb') as handle:
        return Image.open(BytesIO(handle.read()))


def test_dimensions_are_stored(ambit, admin_user):
    file_obj = upload_image(ambit, admin_user, Image.new('RGB', (640, 480)))
    assert (file_obj.width, file_obj.height) == (640, 480)
    file_obj.refresh_from_db()
    assert (file_obj.width, file_obj.height) == (640, 480)


def test_image_within_the_limit_is_stored_unchanged(ambit, admin_user):
    original = Image.new('RGB', (PILImageModel.MAX_STORED_IMAGE_WIDTH, 100))
    file_obj = upload_image(ambit, admin_user, original)

    assert (file_obj.width, file_obj.height) == (PILImageModel.MAX_STORED_IMAGE_WIDTH, 100)
    assert stored_image(ambit, file_obj).size == (PILImageModel.MAX_STORED_IMAGE_WIDTH, 100)


def test_oversized_image_is_downscaled_on_disk(ambit, admin_user):
    """Uploads wider than MAX_STORED_IMAGE_WIDTH are resized before they are stored, so that a huge
    original cannot fill up the storage."""
    original = Image.new('RGB', (2 * PILImageModel.MAX_STORED_IMAGE_WIDTH, 1000))
    file_obj = upload_image(ambit, admin_user, original, name='huge.png')

    expected_size = (PILImageModel.MAX_STORED_IMAGE_WIDTH, 500)
    assert (file_obj.width, file_obj.height) == expected_size
    assert stored_image(ambit, file_obj).size == expected_size
    # file size and checksum describe the resized payload, not the upload
    assert file_obj.file_size == ambit.original_storage.size(file_obj.file_path)
    assert len(file_obj.sha1) == 40


def test_portrait_image_is_not_downscaled_by_its_height(ambit, admin_user):
    original = Image.new('RGB', (100, 2 * PILImageModel.MAX_STORED_IMAGE_WIDTH))
    file_obj = upload_image(ambit, admin_user, original)
    assert (file_obj.width, file_obj.height) == (100, 2 * PILImageModel.MAX_STORED_IMAGE_WIDTH)


@pytest.mark.parametrize('orientation, rotated', [
    (1, False),  # no rotation
    (3, False),  # upside down, dimensions are kept
    (6, True),   # camera held sideways — the common case for phone photos
    (8, True),
])
def test_exif_orientation_is_applied_before_storing(ambit, admin_user, orientation, rotated):
    original = Image.new('RGB', (100, 50))
    exif = original.getexif()
    exif[ExifTags.Base.Orientation] = orientation
    file_obj = upload_image(
        ambit, admin_user, original, name='rotated.jpg', image_format='JPEG', exif=exif.tobytes(),
    )

    expected_size = (50, 100) if rotated else (100, 50)
    assert (file_obj.width, file_obj.height) == expected_size
    assert stored_image(ambit, file_obj).size == expected_size


def test_rotated_image_is_stored_without_its_orientation_tag(ambit, admin_user):
    """The pixels are rotated already, so a surviving orientation tag would rotate them a second time."""
    original = Image.new('RGB', (100, 50))
    exif = original.getexif()
    exif[ExifTags.Base.Orientation] = 6
    file_obj = upload_image(
        ambit, admin_user, original, name='rotated.jpg', image_format='JPEG', exif=exif.tobytes(),
    )

    assert stored_image(ambit, file_obj).getexif().get(ExifTags.Base.Orientation) is None


def test_exif_headers_are_kept_as_meta_data(ambit, admin_user):
    original = Image.new('RGB', (100, 50))
    exif = original.getexif()
    exif[ExifTags.Base.Make] = 'DjangoFinder'
    exif[ExifTags.Base.Model] = 'TestCamera'
    file_obj = upload_image(
        ambit, admin_user, original, name='camera.jpg', image_format='JPEG', exif=exif.tobytes(),
    )

    assert file_obj.meta_data['exif']['Make'] == 'DjangoFinder'
    assert file_obj.meta_data['exif']['Model'] == 'TestCamera'


def test_broken_payload_is_stored_without_dimensions(ambit, admin_user):
    """A file which PIL cannot open is kept, but has no dimensions — it must not break the upload."""
    uploaded_file = SimpleUploadedFile('broken.png', b'this is not a PNG', content_type='image/png')
    file_obj = PILImageModel.objects.create_from_upload(
        ambit, uploaded_file, folder=ambit.root_folder, owner=admin_user,
    )
    assert (file_obj.width, file_obj.height) == (0, 0)
    assert ambit.original_storage.exists(file_obj.file_path) is True
