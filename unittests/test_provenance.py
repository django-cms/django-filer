"""
Tests for detecting and keeping the provenance of images: the IPTC digital source type,
which e.g. marks images created using generative AI, and embedded C2PA Content Credentials.
"""
import pytest
import struct
import zlib
from io import BytesIO, StringIO

from PIL import ExifTags, Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.contrib.image.models import ImageFileModel
from finder.contrib.image.pil.models import PILImageModel
from finder.utils.provenance import (
    C2PA_ISOBMFF_UUID,
    IPTC_DIGITAL_SOURCE_TYPE_BASE,
    Provenance,
    detect_content_credentials,
    detect_digital_source_type,
    detect_file_provenance,
    get_digital_source_type_label,
    is_ai_digital_source_type,
    normalize_digital_source_type,
    provenance_meta_data,
    read_xmp_packet,
)


AI_GENERATED = IPTC_DIGITAL_SOURCE_TYPE_BASE + 'trainedAlgorithmicMedia'
AI_EDITED = IPTC_DIGITAL_SOURCE_TYPE_BASE + 'compositeWithTrainedAlgorithmicMedia'
CAPTURE = IPTC_DIGITAL_SOURCE_TYPE_BASE + 'digitalCapture'


def xmp_packet(digital_source_type=AI_GENERATED, form='attribute'):
    namespaces = (
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"'
    )
    if form == 'attribute':
        description = (
            f'<rdf:Description rdf:about="" {namespaces} '
            f'Iptc4xmpExt:DigitalSourceType="{digital_source_type}"/>'
        )
    elif form == 'element':
        description = (
            f'<rdf:Description rdf:about="" {namespaces}>'
            f'<Iptc4xmpExt:DigitalSourceType>\n  {digital_source_type}\n</Iptc4xmpExt:DigitalSourceType>'
            f'</rdf:Description>'
        )
    else:
        description = (
            f'<rdf:Description rdf:about="" {namespaces}>'
            f'<Iptc4xmpExt:DigitalSourceType rdf:resource="{digital_source_type}"/>'
            f'</rdf:Description>'
        )
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF '
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        f'{description}</rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
    ).encode()


def jumbf_c2pa_box():
    description = b'jumd' + bytes(16) + b'\x03' + b'c2pa\x00'
    description = struct.pack('>I', len(description) + 4) + description
    return struct.pack('>I', len(description) + 8) + b'jumb' + description


def jpeg_segment(marker, payload):
    return b'\xff' + bytes((marker,)) + struct.pack('>H', len(payload) + 2) + payload


def jpeg_bytes(xmp=None, c2pa=False, size=(40, 30), **save_kwargs):
    buffer = BytesIO()
    Image.new('RGB', size, color=(200, 100, 50)).save(buffer, 'JPEG', **save_kwargs)
    data = buffer.getvalue()
    segments = b''
    if xmp is not None:
        segments += jpeg_segment(0xE1, b'http://ns.adobe.com/xap/1.0/\x00' + xmp)
    if c2pa:
        segments += jpeg_segment(0xEB, b'JP' + b'\x00\x01' + b'\x00\x00\x00\x01' + jumbf_c2pa_box())
    return data[:2] + segments + data[2:]


def png_chunk(chunk_type, data):
    return struct.pack('>I', len(data)) + chunk_type + data + struct.pack('>I', zlib.crc32(chunk_type + data))


def png_bytes(xmp=None, c2pa=False, size=(40, 30)):
    from PIL.PngImagePlugin import PngInfo

    pnginfo = PngInfo()
    if xmp is not None:
        pnginfo.add_itxt('XML:com.adobe.xmp', xmp.decode())
    buffer = BytesIO()
    Image.new('RGB', size, color=(200, 100, 50)).save(buffer, 'PNG', pnginfo=pnginfo)
    data = buffer.getvalue()
    if c2pa:
        iend = data.rindex(b'IEND') - 4
        data = data[:iend] + png_chunk(b'caBX', jumbf_c2pa_box()) + data[iend:]
    return data


def png_bytes_with_late_xmp(xmp, compressed=False):
    """PNG with the XMP iTXt chunk after the image data, where Pillow does not read it
    without decoding the image."""
    data = png_bytes()
    text = zlib.compress(xmp) if compressed else xmp
    chunk = png_chunk(b'iTXt', b'XML:com.adobe.xmp\x00' + bytes((int(compressed), 0)) + b'\x00\x00' + text)
    iend = data.rindex(b'IEND') - 4
    return data[:iend] + chunk + data[iend:]


def gif_sub_blocks(data):
    return b''.join(bytes((len(data[i:i + 255]),)) + data[i:i + 255] for i in range(0, len(data), 255)) + b'\x00'


def gif_bytes(xmp=None, c2pa=False, comment=None):
    buffer = BytesIO()
    kwargs = {'comment': comment} if comment else {}
    Image.new('RGB', (40, 30), color=(200, 100, 50)).convert('P').save(buffer, 'GIF', **kwargs)
    data = buffer.getvalue()
    if c2pa:
        # C2PA_GIF application extension before the first image
        extension = b'!\xff\x0b' + b'C2PA_GIF\x01\x00\x00' + gif_sub_blocks(jumbf_c2pa_box())
        flags = data[10]  # logical screen descriptor, followed by the global color table
        position = 13 + (3 << ((flags & 7) + 1) if flags & 0x80 else 0)
        data = data[:position] + extension + data[position:]
    if xmp is None:
        return data
    magic_trailer = b'\x01' + bytes(range(255, -1, -1)) + b'\x00'
    extension = b'!\xff\x0b' + b'XMP DataXMP' + xmp + magic_trailer
    # after the image data, before the GIF trailer
    return data[:-1] + extension + data[-1:]


def riff_chunk(fourcc, data):
    return fourcc + struct.pack('<I', len(data)) + data + (b'\x00' if len(data) & 1 else b'')


def webp_bytes(c2pa=False):
    chunks = riff_chunk(b'VP8X', bytes(10)) + riff_chunk(b'ICCP', b'odd')
    if c2pa:
        chunks += riff_chunk(b'C2PA', jumbf_c2pa_box())
    return b'RIFF' + struct.pack('<I', len(chunks) + 4) + b'WEBP' + chunks


def isobmff_box(box_type, data):
    return struct.pack('>I', len(data) + 8) + box_type + data


def avif_bytes(c2pa=False, other_uuid=False):
    boxes = isobmff_box(b'ftyp', b'avif' + bytes(4) + b'mif1avif')
    if other_uuid:
        boxes += isobmff_box(b'uuid', bytes(16) + b'payload')
    if c2pa:
        boxes += isobmff_box(b'uuid', C2PA_ISOBMFF_UUID + bytes(4) + b'manifest' + jumbf_c2pa_box())
    return boxes + isobmff_box(b'mdat', bytes(32))


def detect(data):
    return detect_digital_source_type(Image.open(BytesIO(data)))


def upload(ambit, owner, data, name='picture.jpg', mime_type='image/jpeg', folder=None):
    uploaded_file = SimpleUploadedFile(name, data, content_type=mime_type)
    return PILImageModel.objects.create_from_upload(
        ambit, uploaded_file, folder=folder or ambit.root_folder, owner=owner, mime_type=mime_type,
    )


def stored_bytes(ambit, image):
    with ambit.original_storage.open(image.file_path, 'rb') as handle:
        return handle.read()


# detection

@pytest.mark.parametrize('form', ['attribute', 'element', 'resource'])
def test_digital_source_type_forms(form):
    assert detect(jpeg_bytes(xmp_packet(AI_EDITED, form=form))) == AI_EDITED


def test_digital_source_type_png_itxt():
    assert detect(png_bytes(xmp_packet())) == AI_GENERATED


@pytest.mark.parametrize('compressed', [False, True])
def test_digital_source_type_png_after_image_data(compressed):
    file = BytesIO(png_bytes_with_late_xmp(xmp_packet(), compressed=compressed))
    image = Image.open(file)
    assert detect_digital_source_type(image) == ''  # not exposed by Pillow
    position = file.tell()
    assert detect_digital_source_type(image, file) == AI_GENERATED
    assert file.tell() == position


def test_digital_source_type_gif():
    file = BytesIO(gif_bytes(xmp_packet(AI_EDITED)))
    assert detect_digital_source_type(Image.open(file), file) == AI_EDITED
    file = BytesIO(gif_bytes())
    assert detect_digital_source_type(Image.open(file), file) == ''


@pytest.mark.parametrize('data', [
    gif_bytes(xmp_packet())[:40],
    gif_bytes(xmp_packet())[:-300],  # magic trailer missing
    png_bytes_with_late_xmp(xmp_packet())[:-40],
    b'GIF89a',
    b'\x89PNG\r\n\x1a\n' + struct.pack('>I4s', 5, b'iTXt') + b'XML:c',
])
def test_malformed_raw_xmp(data):
    assert read_xmp_packet(BytesIO(data)) == b''


def test_digital_source_type_values():
    assert detect(jpeg_bytes(xmp_packet('trainedAlgorithmicMedia'))) == AI_GENERATED
    assert detect(jpeg_bytes()) == ''
    assert detect(png_bytes()) == ''
    assert detect(jpeg_bytes(b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF/></x:xmpmeta>')) == ''
    assert normalize_digital_source_type('') == ''
    assert normalize_digital_source_type('not a uri') == ''
    assert normalize_digital_source_type('javascript:alert(1)') == ''
    assert normalize_digital_source_type('http://example.com/' + 'x' * 300) == ''


def test_classification():
    assert is_ai_digital_source_type(AI_GENERATED)
    assert is_ai_digital_source_type(AI_EDITED)
    assert not is_ai_digital_source_type(CAPTURE)
    assert not is_ai_digital_source_type('')
    assert str(get_digital_source_type_label(AI_GENERATED)) == "Created using generative AI"
    assert get_digital_source_type_label('http://example.com/vocab/unknownTerm') == 'unknownTerm'


@pytest.mark.parametrize('data, expected', [
    (jpeg_bytes(c2pa=True), True),
    (jpeg_bytes(xmp_packet(), c2pa=True), True),
    (jpeg_bytes(xmp_packet()), False),
    (png_bytes(c2pa=True), True),
    (png_bytes(xmp_packet()), False),
    (webp_bytes(c2pa=True), True),
    (webp_bytes(), False),
    (gif_bytes(c2pa=True), True),
    (gif_bytes(xmp_packet()), False),
    (gif_bytes(comment=b'C2PA_GIF'), False),
    (avif_bytes(c2pa=True, other_uuid=True), True),
    (avif_bytes(other_uuid=True), False),
    # malformed files
    (b'', False),
    (b'\xff\xd8\xff\xeb\x00', False),
    (jpeg_bytes(c2pa=True)[:30], False),
    (png_bytes(c2pa=True)[:20], False),
    (b'RIFF\x00\x00\x00\x00WEBPC2P', False),
    (struct.pack('>I', 4) + b'ftyp', False),
    (b'GIF89a' + bytes(20), False),
])
def test_content_credentials(data, expected):
    assert detect_content_credentials(BytesIO(data)) is expected


def test_detect_file_provenance():
    file = BytesIO(jpeg_bytes(xmp_packet(), c2pa=True))
    file.seek(10)
    assert detect_file_provenance(file) == Provenance(AI_GENERATED, True)
    assert file.tell() == 0
    assert detect_file_provenance(BytesIO(b'<svg/>')) == Provenance()


def test_provenance_meta_data():
    assert provenance_meta_data(Provenance()) is None
    assert provenance_meta_data(Provenance(CAPTURE)) == {
        'digital_source_type': CAPTURE,
        'content_credentials': False,
        'ai_generated': False,
    }
    assert provenance_meta_data(Provenance('', True))['content_credentials'] is True


# model

def test_upload_detects_provenance(ambit, admin_user):
    image = upload(ambit, admin_user, jpeg_bytes(xmp_packet(), c2pa=True))
    image = PILImageModel.objects.get(pk=image.pk)
    assert image.meta_data['provenance'] == {
        'digital_source_type': AI_GENERATED,
        'content_credentials': True,
        'ai_generated': True,
    }
    assert image.is_ai_generated
    assert str(image.digital_source_type_label) == "Created using generative AI"
    assert image.get_meta_data()['provenance'] == {
        'origin': "Created using generative AI",
        'ai_generated': True,
        'content_credentials': True,
    }


def test_upload_keeps_original_bytes(ambit, admin_user):
    data = jpeg_bytes(xmp_packet(), c2pa=True)
    image = upload(ambit, admin_user, data)
    assert stored_bytes(ambit, image) == data


@pytest.mark.parametrize('data, name, mime_type', [
    (png_bytes_with_late_xmp(xmp_packet()), 'picture.png', 'image/png'),
    (gif_bytes(xmp_packet()), 'picture.gif', 'image/gif'),
])
def test_upload_detects_provenance_not_exposed_by_pillow(ambit, admin_user, data, name, mime_type):
    image = upload(ambit, admin_user, data, name=name, mime_type=mime_type)
    assert image.is_ai_generated


def test_upload_without_provenance(ambit, admin_user, uploaded_image):
    assert 'provenance' not in uploaded_image.meta_data
    assert uploaded_image.provenance == Provenance()
    assert not uploaded_image.is_ai_generated
    assert 'provenance' not in uploaded_image.get_meta_data()


def test_svg_has_no_provenance(ambit, admin_user):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
    uploaded_file = SimpleUploadedFile('drawing.svg', svg, content_type='image/svg+xml')
    image = ImageFileModel.objects.create_from_upload(
        ambit, uploaded_file, folder=ambit.root_folder, owner=admin_user, mime_type='image/svg+xml',
    )
    assert 'provenance' not in image.meta_data


def strip_everything(file_name, file, owner, mime_type):
    image = Image.open(file)
    image.load()
    buffer = BytesIO()
    image.save(buffer, image.format)
    file.seek(0)
    file.truncate()
    file.write(buffer.getvalue())


def test_provenance_is_detected_before_payload_validators(ambit, admin_user, settings):
    settings.FINDER_PAYLOAD_VALIDATORS = {'image/*': [strip_everything]}
    image = upload(ambit, admin_user, jpeg_bytes(xmp_packet(), c2pa=True))
    stored = BytesIO(stored_bytes(ambit, image))
    assert detect_file_provenance(stored) == Provenance()
    assert image.provenance == Provenance(AI_GENERATED, True)


def test_reencoding_on_orientation_keeps_digital_source_type(ambit, admin_user):
    exif = Image.new('RGB', (1, 1)).getexif()
    exif[ExifTags.Base.Orientation] = 6
    data = jpeg_bytes(xmp_packet(), c2pa=True, size=(100, 50), exif=exif.tobytes())
    image = upload(ambit, admin_user, data)
    assert (image.width, image.height) == (50, 100)  # re-encoded
    stored = BytesIO(stored_bytes(ambit, image))
    # the signature of a C2PA manifest does not cover the re-encoded image
    assert detect_file_provenance(stored) == Provenance(AI_GENERATED, False)
    assert image.provenance == Provenance(AI_GENERATED, True)


@pytest.mark.parametrize('data, name, mime_type', [
    (png_bytes(xmp_packet(AI_EDITED), size=(2 * PILImageModel.MAX_STORED_IMAGE_WIDTH, 10)), 'huge.png', 'image/png'),
    (jpeg_bytes(xmp_packet(AI_EDITED), size=(2 * PILImageModel.MAX_STORED_IMAGE_WIDTH, 10)), 'huge.jpg', 'image/jpeg'),
])
def test_downscaling_keeps_digital_source_type(ambit, admin_user, data, name, mime_type):
    image = upload(ambit, admin_user, data, name=name, mime_type=mime_type)
    assert image.width == PILImageModel.MAX_STORED_IMAGE_WIDTH
    stored = BytesIO(stored_bytes(ambit, image))
    assert detect_file_provenance(stored).digital_source_type == AI_EDITED


def test_reencoding_without_provenance_adds_no_xmp(ambit, admin_user):
    data = png_bytes(size=(2 * PILImageModel.MAX_STORED_IMAGE_WIDTH, 10))
    image = upload(ambit, admin_user, data, name='huge.png', mime_type='image/png')
    assert b'XML:com.adobe.xmp' not in stored_bytes(ambit, image)


def test_copy_keeps_provenance(ambit, admin_user, sub_folder):
    image = upload(ambit, admin_user, jpeg_bytes(xmp_packet()))
    copy = image.copy_to(ambit, admin_user, sub_folder)
    assert PILImageModel.objects.get(pk=copy.pk).is_ai_generated


# admin

def replace_file(admin_client, image, data, name='picture.jpg', mime_type='image/jpeg'):
    upload_url = f"{reverse('admin:finder_filemodel_changelist')}{image.id}/upload"
    response = admin_client.post(
        upload_url,
        {'upload_file': SimpleUploadedFile(name, data, content_type=mime_type)},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 200
    return PILImageModel.objects.get(pk=image.pk)


def test_replacing_file_replaces_provenance(admin_client, ambit, admin_user):
    image = upload(ambit, admin_user, jpeg_bytes(xmp_packet(), c2pa=True))
    image = replace_file(admin_client, image, jpeg_bytes(xmp_packet(CAPTURE)))
    assert image.provenance == Provenance(CAPTURE, False)
    image = replace_file(admin_client, image, jpeg_bytes())
    assert 'provenance' not in image.meta_data


def test_change_view_shows_provenance(admin_client, ambit, admin_user):
    image = upload(ambit, admin_user, jpeg_bytes(xmp_packet(), c2pa=True))
    response = admin_client.get(f'/admin/finder/{ambit.slug}/{image.id}')
    assert response.status_code == 200
    content = response.content.decode()
    assert "Created using generative AI" in content
    assert "found on upload, not verified" in content


def test_change_view_without_provenance(admin_client, ambit, uploaded_image):
    response = admin_client.get(f'/admin/finder/{ambit.slug}/{uploaded_image.id}')
    assert response.status_code == 200
    assert "Content Credentials" not in response.content.decode()


# filtering

@pytest.fixture
def images(ambit, admin_user, sub_folder):
    return {
        'ai': upload(ambit, admin_user, jpeg_bytes(xmp_packet()), name='ai.jpg'),
        'c2pa': upload(ambit, admin_user, jpeg_bytes(c2pa=True), name='c2pa.jpg'),
        'capture': upload(ambit, admin_user, jpeg_bytes(xmp_packet(CAPTURE)), name='capture.jpg'),
        'plain': upload(ambit, admin_user, jpeg_bytes(), name='plain.jpg'),
    }


@pytest.mark.parametrize('cookie, expected', [
    ('ai', {'ai'}),
    ('c2pa', {'c2pa'}),
    ('ai,c2pa', {'ai', 'c2pa'}),
    ('unknown', {'ai', 'c2pa', 'capture', 'plain'}),
])
def test_browser_list_filtered_by_provenance(admin_client, ambit, images, cookie, expected):
    admin_client.cookies['django-finder-provenance'] = cookie
    api_url = reverse('finder-api:base-url')
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    ids = {entry['id'] for entry in response.json()['files']}
    assert ids == {str(images[key].id) for key in expected}


def test_browser_search_filtered_by_provenance(admin_client, ambit, images):
    admin_client.cookies['django-finder-provenance'] = 'ai'
    api_url = reverse('finder-api:base-url')
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/search?q=.jpg')
    assert [entry['id'] for entry in response.json()['files']] == [str(images['ai'].id)]


def test_admin_fetch_filtered_by_provenance_keeps_folders(admin_client, ambit, images, sub_folder):
    admin_client.cookies['django-finder-provenance'] = 'c2pa'
    base_url = reverse('admin:finder_inodemodel_change', args=(ambit.root_folder_id,))
    response = admin_client.get(f'{base_url}/fetch')
    ids = {inode['id'] for inode in response.json()['inodes']}
    assert ids == {str(sub_folder.id), str(images['c2pa'].id)}


# management command

def test_detect_provenance_command(ambit, admin_user):
    image = upload(ambit, admin_user, jpeg_bytes(xmp_packet(), c2pa=True))
    plain = upload(ambit, admin_user, jpeg_bytes(), name='plain.jpg')
    # as if uploaded before finder detected provenance
    PILImageModel.objects.filter(pk=image.pk).update(meta_data={'alt_text': "Robot"})
    last_modified_at = PILImageModel.objects.get(pk=image.pk).last_modified_at

    stdout = StringIO()
    call_command('finder', 'detect-provenance', '--dry-run', stdout=stdout)
    assert "Scanned 2 images, would update 1, failed 0." in stdout.getvalue()
    assert 'provenance' not in PILImageModel.objects.get(pk=image.pk).meta_data

    stdout = StringIO()
    call_command('finder', 'detect-provenance', stdout=stdout, verbosity=2)
    assert "Scanned 2 images, updated 1, failed 0." in stdout.getvalue()
    image = PILImageModel.objects.get(pk=image.pk)
    assert image.provenance == Provenance(AI_GENERATED, True)
    assert image.meta_data['alt_text'] == "Robot"
    assert image.last_modified_at == last_modified_at
    assert 'provenance' not in PILImageModel.objects.get(pk=plain.pk).meta_data

    # images with provenance are not scanned again
    stdout = StringIO()
    call_command('finder', 'detect-provenance', stdout=stdout)
    assert "Scanned 1 images, updated 0, failed 0." in stdout.getvalue()


def test_detect_provenance_command_missing_file(ambit, admin_user):
    image = upload(ambit, admin_user, jpeg_bytes())
    ambit.original_storage.delete(image.file_path)
    stdout, stderr = StringIO(), StringIO()
    call_command('finder', 'detect-provenance', stdout=stdout, stderr=stderr)
    assert "failed 1." in stdout.getvalue()
    assert f"({image.pk})" in stderr.getvalue()


def test_admin_fetch_shows_origin_of_ai_images(admin_client, ambit, images):
    base_url = reverse('admin:finder_inodemodel_change', args=(ambit.root_folder_id,))
    response = admin_client.get(f'{base_url}/fetch')
    origins = {inode['id']: inode.get('origin') for inode in response.json()['inodes']}
    assert origins[str(images['ai'].id)] == "Created using generative AI"
    # other digital source types are shown on the change form only
    assert origins[str(images['capture'].id)] is None
    assert origins[str(images['plain'].id)] is None
