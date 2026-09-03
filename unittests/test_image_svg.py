import pytest
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

from finder.contrib.image.svg.models import SVGImageModel
from finder.exceptions import FileValidationError
from finder.utils import svg


SIMPLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480" viewBox="0 0 64 48">'
    '<rect x="0" y="0" width="64" height="48" fill="#123456"/>'
    '</svg>'
)


def make_svg(markup=SIMPLE_SVG, name='test_image.svg'):
    return SimpleUploadedFile(name, markup.encode(), content_type='image/svg+xml')


def break_stored_svg(ambit, owner, name, markup='<svg><rect></svg>'):
    """
    Upload a sound SVG, then replace the stored document with an unparseable one.

    The sanitizing validator rejects a malformed SVG on upload, so a document this
    broken can only reach the storage afterwards — by an outside write, or by having
    been stored before the validator existed.
    """
    image = SVGImageModel.objects.create_from_upload(
        ambit,
        make_svg(name=name),
        folder=ambit.root_folder,
        owner=owner,
    )
    ambit.original_storage.delete(image.file_path)
    ambit.original_storage.save(image.file_path, ContentFile(markup.encode()))
    return image


@pytest.fixture
def uploaded_svg(ambit, admin_user):
    return SVGImageModel.objects.create_from_upload(
        ambit,
        make_svg(),
        folder=ambit.root_folder,
        owner=admin_user,
    )


class TestParseLength:
    @pytest.mark.parametrize('value, expected', [
        ('12', 12.0),
        ('12px', 12.0),
        (' 12.5 px ', 12.5),
        ('1in', 96.0),
        ('72pt', 96.0),
        ('2.54cm', 96.0),
        ('-3', -3.0),
    ])
    def test_absolute_lengths(self, value, expected):
        assert svg.parse_length(value) == pytest.approx(expected)

    @pytest.mark.parametrize('value', ['', None, '100%', '3em', '10vw', 'auto', '1e999', 'twelve'])
    def test_unusable_lengths(self, value):
        assert svg.parse_length(value) is None


class TestParseViewbox:
    def test_separators(self):
        assert svg.parse_viewbox('0 0 64 48') == (0, 0, 64, 48)
        assert svg.parse_viewbox('0,0,64,48') == (0, 0, 64, 48)
        assert svg.parse_viewbox(' -1 -2  64 , 48 ') == (-1, -2, 64, 48)

    @pytest.mark.parametrize('value', [
        '', None, '0 0 64', '0 0 64 48 32', '0 0 nan 48', '0 0 inf 48', '0 0 0 48', '0 0 -64 48', 'a b c d',
    ])
    def test_unusable_viewboxes(self, value):
        assert svg.parse_viewbox(value) is None


class TestLoad:
    def test_dimensions_from_attributes(self):
        assert svg.get_dimensions(BytesIO(SIMPLE_SVG.encode())) == (640.0, 480.0)

    def test_dimensions_from_viewbox(self):
        markup = '<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 64 48"/>'
        assert svg.get_dimensions(BytesIO(markup.encode())) == (64.0, 48.0)

    def test_unit_conversion(self):
        markup = '<svg xmlns="http://www.w3.org/2000/svg" width="1in" height="72pt"/>'
        assert svg.get_dimensions(BytesIO(markup.encode())) == (96.0, 96.0)

    def test_missing_size_without_viewbox(self):
        markup = '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"/>'
        with pytest.raises(ValueError, match='no usable width and height'):
            svg.load(BytesIO(markup.encode()))

    def test_missing_viewbox_implies_one(self):
        markup = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="48"/>'
        image = svg.load(BytesIO(markup.encode()))
        assert image.viewbox == (0.0, 0.0, 64.0, 48.0)

    def test_accepts_str_and_path(self, tmp_path):
        path = tmp_path / 'image.svg'
        path.write_text(SIMPLE_SVG)
        assert svg.get_dimensions(path) == (640.0, 480.0)
        assert svg.get_dimensions(str(path)) == (640.0, 480.0)

    def test_rejects_non_svg_root(self):
        with pytest.raises(ValueError, match='not <svg>'):
            svg.load(BytesIO(b'<html><body/></html>'))

    def test_rejects_malformed_xml(self):
        with pytest.raises(ValueError, match='Cannot parse'):
            svg.load(BytesIO(b'<svg><rect></svg>'))

    def test_rejects_entity_declarations(self):
        # "billion laughs": xml.etree expands internal entities.
        markup = (
            '<?xml version="1.0"?>'
            '<!DOCTYPE svg [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]>'
            '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">&lol2;</svg>'
        )
        with pytest.raises(ValueError, match='XML entities'):
            svg.load(BytesIO(markup.encode()))


class TestSvgImage:
    def test_crop_maps_onto_viewbox(self):
        # 640x480 rendered from a 64x48 user space: pixels map at 1:10.
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        cropped = image.crop((80, 40, 400, 280))
        assert cropped.size == (320.0, 240.0)
        assert cropped.viewbox == (8.0, 4.0, 32.0, 24.0)
        assert cropped.root.get('viewBox') == '8 4 32 24'
        assert cropped.root.get('width') == '320'

    def test_crop_leaves_the_original_alone(self):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        image.crop((0, 0, 32, 24))
        assert image.size == (640.0, 480.0)
        assert image.viewbox == (0.0, 0.0, 64.0, 48.0)

    @pytest.mark.parametrize('box', [None, (10, 10, 10, 10), (10, 10, 0, 0)])
    def test_degenerate_crop_box_returns_a_copy(self, box):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        assert image.crop(box).size == (640.0, 480.0)

    def test_resize_keeps_the_viewbox(self):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        resized = image.resize((64, 48))
        assert resized.size == (64.0, 48.0)
        assert resized.viewbox == (0.0, 0.0, 64.0, 48.0)

    def test_thumbnail_preserves_aspect_ratio(self):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        image.thumbnail((180, 180))
        assert image.size == (180.0, 135.0)

    def test_thumbnail_does_not_enlarge(self):
        # PIL.Image.thumbnail() refuses to as well, so both backends agree.
        markup = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="24"/>'
        image = svg.load(BytesIO(markup.encode()))
        image.thumbnail((180, 180))
        assert image.size == (32.0, 24.0)

    @pytest.mark.parametrize('size', [(0, 180), (180, -1)])
    def test_thumbnail_rejects_invalid_sizes(self, size):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        with pytest.raises(ValueError, match='Invalid thumbnail size'):
            image.thumbnail(size)

    def test_save_to_binary_and_text_targets(self, tmp_path):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        binary = BytesIO()
        image.save(binary, format='SVG')
        assert svg.load(BytesIO(binary.getvalue())).size == (640.0, 480.0)

        path = tmp_path / 'out.svg'
        image.save(path)
        assert svg.get_dimensions(path) == (640.0, 480.0)

    def test_save_rejects_other_formats(self):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        with pytest.raises(ValueError, match="expected to be 'SVG'"):
            image.save(BytesIO(), format='PNG')

    def test_serialization_keeps_the_default_namespace(self):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        assert b'xmlns="http://www.w3.org/2000/svg"' in image.tobytes()
        assert b'ns0:' not in image.tobytes()

    def test_vector_content_survives(self):
        image = svg.load(BytesIO(SIMPLE_SVG.encode()))
        cropped = image.crop((0, 0, 320, 240))
        assert cropped.root.find('{http://www.w3.org/2000/svg}rect').get('fill') == '#123456'


@pytest.mark.django_db
class TestSVGImageModel:
    def test_upload_reads_dimensions(self, uploaded_svg):
        assert isinstance(uploaded_svg, SVGImageModel)
        assert uploaded_svg.width == 640
        assert uploaded_svg.height == 480

    def test_upload_without_readable_dimensions(self, ambit, admin_user):
        markup = '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"/>'
        image = SVGImageModel.objects.create_from_upload(
            ambit,
            make_svg(markup, name='relative.svg'),
            folder=ambit.root_folder,
            owner=admin_user,
        )
        assert (image.width, image.height) == (0, 0)
        # no dimensions, no thumbnail: the generic icon stands in
        assert image.get_thumbnail_url(ambit) == image.fallback_thumbnail_url

    def test_thumbnail_is_a_rescaled_document(self, ambit, uploaded_svg):
        url = uploaded_svg.get_thumbnail_url(ambit)
        assert url != uploaded_svg.fallback_thumbnail_url

        path = f'{uploaded_svg.id}/{uploaded_svg.get_cropped_filename(180, 180)}'
        assert ambit.sample_storage.exists(path)
        with ambit.sample_storage.open(path) as handle:
            thumbnail = svg.load(handle)
        assert thumbnail.size == (180.0, 180.0)
        # a square thumbnail of a 4:3 image is a centered crop, not a squeeze
        assert thumbnail.viewbox[2] == pytest.approx(thumbnail.viewbox[3])
        assert thumbnail.root.find('{http://www.w3.org/2000/svg}rect') is not None

    def test_thumbnail_is_generated_once(self, ambit, uploaded_svg):
        first = uploaded_svg.get_thumbnail_url(ambit)
        path = f'{uploaded_svg.id}/{uploaded_svg.get_cropped_filename(180, 180)}'
        with ambit.sample_storage.open(path) as handle:
            content = handle.read()
        assert uploaded_svg.get_thumbnail_url(ambit) == first
        with ambit.sample_storage.open(path) as handle:
            assert handle.read() == content

    def test_thumbnail_honours_the_crop_box(self, ambit, uploaded_svg):
        uploaded_svg.crop_x, uploaded_svg.crop_y, uploaded_svg.crop_size = 0.0, 0.0, 240.0
        uploaded_svg.save(update_fields=['crop_x', 'crop_y', 'crop_size'])
        path = f'{uploaded_svg.id}/{uploaded_svg.get_cropped_filename(180, 180)}'
        uploaded_svg.crop(ambit, path, 180, 180)
        with ambit.sample_storage.open(path) as handle:
            thumbnail = svg.load(handle)
        # user space is 1/10th of the pixel space
        assert thumbnail.viewbox[0] == pytest.approx(0.0)
        assert thumbnail.viewbox[2] == pytest.approx(24.0)

    def test_crop_reports_unparseable_documents(self, ambit, admin_user):
        image = break_stored_svg(ambit, admin_user, name='broken.svg')
        with pytest.raises(FileValidationError):
            image.crop(ambit, f'{image.id}/broken__180x180.svg', 180, 180)

    def test_broken_document_falls_back_to_the_icon(self, ambit, admin_user):
        image = break_stored_svg(ambit, admin_user, name='broken2.svg')
        assert image.get_thumbnail_url(ambit) == image.fallback_thumbnail_url
