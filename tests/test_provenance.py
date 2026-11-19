import io
import struct
import zlib
from unittest import mock

from django.apps import apps
from django.contrib.admin import helpers
from django.core.files import File as DjangoFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from easy_thumbnails.files import get_thumbnailer

from filer import settings as filer_settings
from filer.models.foldermodels import Folder
from filer.settings import FILER_IMAGE_MODEL
from filer.utils import provenance
from filer.utils.compatibility import PILImage, PILImageDraw
from filer.utils.loader import load_model
from filer.utils.provenance import (
    C2PA_ISOBMFF_UUID,
    IPTC_DIGITAL_SOURCE_TYPE_BASE,
    build_xmp_packet,
    detect_content_credentials,
    detect_digital_source_type,
    detect_file_provenance,
    detect_provenance,
    embed_xmp,
    get_c2pa_digital_source_type,
    get_digital_source_type_choices,
    get_digital_source_type_label,
    get_xmp_packet,
    insert_jpeg_xmp,
    is_ai_digital_source_type,
    normalize_digital_source_type,
    read_content_credentials,
    read_xmp_packet,
)
from filer.validation import strip_exif
from tests.helpers import create_image, create_superuser


Image = load_model(FILER_IMAGE_MODEL)

AI_GENERATED = IPTC_DIGITAL_SOURCE_TYPE_BASE + "trainedAlgorithmicMedia"
AI_EDITED = IPTC_DIGITAL_SOURCE_TYPE_BASE + "compositeWithTrainedAlgorithmicMedia"
CAPTURE = IPTC_DIGITAL_SOURCE_TYPE_BASE + "digitalCapture"


def xmp_packet(digital_source_type=AI_GENERATED, form="attribute"):
    namespaces = (
        'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
        'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"'
    )
    if form == "attribute":
        description = (
            f'<rdf:Description rdf:about="" {namespaces} '
            f'Iptc4xmpExt:DigitalSourceType="{digital_source_type}"/>'
        )
    elif form == "element":
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


def cbor_text(value):
    value = value.encode()
    if len(value) < 24:
        return bytes((0x60 + len(value),)) + value
    if len(value) < 256:
        return b"\x78" + bytes((len(value),)) + value
    return b"\x79" + struct.pack(">H", len(value)) + value


def c2pa_action(digital_source_type):
    """The part of a CBOR actions assertion stating the digital source type."""
    return (
        cbor_text("action") + cbor_text("c2pa.created")
        + cbor_text("digitalSourceType") + cbor_text(digital_source_type)
    )


def jumbf_c2pa_box(digital_source_type=True):
    """A stand-in for a C2PA manifest store. Pass a digital source type to have
    it stated by an action."""
    description = b"jumd" + bytes(16) + b"\x03" + b"c2pa\x00"
    description = struct.pack(">I", len(description) + 4) + description
    if digital_source_type is not True:
        description += c2pa_action(digital_source_type)
    return struct.pack(">I", len(description) + 8) + b"jumb" + description


def jpeg_segment(marker, payload):
    return b"\xff" + bytes((marker,)) + struct.pack(">H", len(payload) + 2) + payload


def jpeg_bytes(xmp=None, c2pa=False):
    buffer = io.BytesIO()
    create_image(size=(40, 30)).save(buffer, "JPEG")
    data = buffer.getvalue()
    segments = b""
    if xmp is not None:
        segments += jpeg_segment(0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + xmp)
    if c2pa:
        segments += jpeg_segment(0xEB, b"JP" + b"\x00\x01" + b"\x00\x00\x00\x01" + jumbf_c2pa_box(c2pa))
    return data[:2] + segments + data[2:]


def png_chunk(chunk_type, data):
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", zlib.crc32(chunk_type + data))


def png_bytes(xmp=None, c2pa=False):
    from PIL.PngImagePlugin import PngInfo

    pnginfo = PngInfo()
    if xmp is not None:
        pnginfo.add_itxt("XML:com.adobe.xmp", xmp.decode())
    buffer = io.BytesIO()
    create_image(size=(40, 30)).save(buffer, "PNG", pnginfo=pnginfo)
    data = buffer.getvalue()
    if c2pa:
        iend = data.rindex(b"IEND") - 4
        data = data[:iend] + png_chunk(b"caBX", jumbf_c2pa_box(c2pa)) + data[iend:]
    return data


def png_bytes_with_late_xmp(xmp, compressed=False):
    """PNG with the XMP iTXt chunk after the image data, where Pillow does not
    read it without decoding the image."""
    buffer = io.BytesIO()
    create_image(size=(40, 30)).save(buffer, "PNG")
    data = buffer.getvalue()
    text = zlib.compress(xmp) if compressed else xmp
    chunk = png_chunk(b"iTXt", b"XML:com.adobe.xmp\x00" + bytes((int(compressed), 0)) + b"\x00\x00" + text)
    iend = data.rindex(b"IEND") - 4
    return data[:iend] + chunk + data[iend:]


def gif_sub_blocks(data):
    return b"".join(bytes((len(data[i:i + 255]),)) + data[i:i + 255] for i in range(0, len(data), 255)) + b"\x00"


def gif_bytes(xmp=None, c2pa=False, comment=None):
    buffer = io.BytesIO()
    kwargs = {"comment": comment} if comment else {}
    create_image(size=(40, 30)).convert("P").save(buffer, "GIF", **kwargs)
    data = buffer.getvalue()
    if c2pa:
        # C2PA_GIF application extension before the first image
        extension = b"!\xff\x0b" + b"C2PA_GIF\x01\x00\x00" + gif_sub_blocks(jumbf_c2pa_box(c2pa))
        position = data.index(b"!") if b"!" in data[13:] else data.index(b",", 13)
        data = data[:position] + extension + data[position:]
    if xmp is None:
        return data
    magic_trailer = b"\x01" + bytes(range(255, -1, -1)) + b"\x00"
    extension = b"!\xff\x0b" + b"XMP DataXMP" + xmp + magic_trailer
    # After the image data, before the GIF trailer
    return data[:-1] + extension + data[-1:]


def riff_chunk(fourcc, data):
    return fourcc + struct.pack("<I", len(data)) + data + (b"\x00" if len(data) & 1 else b"")


def webp_bytes(c2pa=False):
    chunks = riff_chunk(b"VP8X", bytes(10)) + riff_chunk(b"ICCP", b"odd")
    if c2pa:
        chunks += riff_chunk(b"C2PA", jumbf_c2pa_box(c2pa))
    return b"RIFF" + struct.pack("<I", len(chunks) + 4) + b"WEBP" + chunks


def isobmff_box(box_type, data):
    return struct.pack(">I", len(data) + 8) + box_type + data


def avif_bytes(c2pa=False, other_uuid=False):
    boxes = isobmff_box(b"ftyp", b"avif" + bytes(4) + b"mif1avif")
    if other_uuid:
        boxes += isobmff_box(b"uuid", bytes(16) + b"payload")
    if c2pa:
        boxes += isobmff_box(b"uuid", C2PA_ISOBMFF_UUID + bytes(4) + b"manifest" + jumbf_c2pa_box(c2pa))
    return boxes + isobmff_box(b"mdat", bytes(32))


class DigitalSourceTypeDetectionTests(TestCase):
    def detect(self, data):
        return detect_digital_source_type(PILImage.open(io.BytesIO(data)))

    def test_attribute_form(self):
        self.assertEqual(self.detect(jpeg_bytes(xmp_packet(form="attribute"))), AI_GENERATED)

    def test_element_form(self):
        self.assertEqual(self.detect(jpeg_bytes(xmp_packet(AI_EDITED, form="element"))), AI_EDITED)

    def test_resource_form(self):
        self.assertEqual(self.detect(jpeg_bytes(xmp_packet(form="resource"))), AI_GENERATED)

    def test_png_itxt(self):
        self.assertEqual(self.detect(png_bytes(xmp_packet())), AI_GENERATED)

    def test_png_xmp_after_image_data(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                data = png_bytes_with_late_xmp(xmp_packet(), compressed=compressed)
                file = io.BytesIO(data)
                image = PILImage.open(file)
                self.assertEqual(detect_digital_source_type(image), "")  # Not exposed by Pillow
                position = file.tell()
                self.assertEqual(detect_digital_source_type(image, file), AI_GENERATED)
                self.assertEqual(file.tell(), position)

    def test_gif(self):
        file = io.BytesIO(gif_bytes(xmp_packet(AI_EDITED)))
        self.assertEqual(detect_digital_source_type(PILImage.open(file), file), AI_EDITED)

    def test_gif_without_xmp(self):
        file = io.BytesIO(gif_bytes())
        self.assertEqual(detect_digital_source_type(PILImage.open(file), file), "")

    def test_malformed_raw_xmp(self):
        for data in (
            gif_bytes(xmp_packet())[:40],
            gif_bytes(xmp_packet())[:-300],  # Magic trailer missing
            png_bytes_with_late_xmp(xmp_packet())[:-40],
            b"GIF89a",
            b"\x89PNG\r\n\x1a\n" + struct.pack(">I4s", 5, b"iTXt") + b"XML:c",
        ):
            with self.subTest(data=data[:12]):
                self.assertEqual(read_xmp_packet(io.BytesIO(data)), b"")

    def test_bare_term_is_expanded(self):
        self.assertEqual(self.detect(jpeg_bytes(xmp_packet("trainedAlgorithmicMedia"))), AI_GENERATED)

    def test_no_metadata(self):
        self.assertEqual(self.detect(jpeg_bytes()), "")
        self.assertEqual(self.detect(png_bytes()), "")

    def test_xmp_without_digital_source_type(self):
        xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF/></x:xmpmeta>'
        self.assertEqual(self.detect(jpeg_bytes(xmp)), "")

    def test_unusable_values_are_ignored(self):
        self.assertEqual(normalize_digital_source_type(""), "")
        self.assertEqual(normalize_digital_source_type("not a uri"), "")
        self.assertEqual(normalize_digital_source_type("javascript:alert(1)"), "")
        self.assertEqual(normalize_digital_source_type("http://example.com/" + "x" * 300), "")

    def test_classification(self):
        self.assertTrue(is_ai_digital_source_type(AI_GENERATED))
        self.assertTrue(is_ai_digital_source_type(AI_EDITED))
        self.assertFalse(is_ai_digital_source_type(CAPTURE))
        self.assertFalse(is_ai_digital_source_type(""))
        self.assertEqual(str(get_digital_source_type_label(AI_GENERATED)), "Created using generative AI")
        self.assertEqual(get_digital_source_type_label("http://example.com/vocab/unknownTerm"), "unknownTerm")


class ContentCredentialsDetectionTests(TestCase):
    def detect(self, data):
        return detect_content_credentials(io.BytesIO(data))

    def test_jpeg(self):
        self.assertTrue(self.detect(jpeg_bytes(c2pa=True)))
        self.assertTrue(self.detect(jpeg_bytes(xmp_packet(), c2pa=True)))
        self.assertFalse(self.detect(jpeg_bytes(xmp_packet())))

    def test_png(self):
        self.assertTrue(self.detect(png_bytes(c2pa=True)))
        self.assertFalse(self.detect(png_bytes(xmp_packet())))

    def test_webp(self):
        self.assertTrue(self.detect(webp_bytes(c2pa=True)))
        self.assertFalse(self.detect(webp_bytes()))

    def test_gif(self):
        self.assertTrue(self.detect(gif_bytes(c2pa=True)))
        self.assertTrue(self.detect(gif_bytes(xmp_packet(), c2pa=True)))
        self.assertFalse(self.detect(gif_bytes(xmp_packet())))
        self.assertFalse(self.detect(gif_bytes(comment=b"C2PA_GIF")))

    def test_isobmff(self):
        self.assertTrue(self.detect(avif_bytes(c2pa=True)))
        self.assertTrue(self.detect(avif_bytes(c2pa=True, other_uuid=True)))
        self.assertFalse(self.detect(avif_bytes(other_uuid=True)))

    def test_malformed_files(self):
        for data in (
            b"",
            b"\xff\xd8",
            b"\xff\xd8\xff\xeb\x00",
            jpeg_bytes(c2pa=True)[:30],
            png_bytes(c2pa=True)[:20],
            b"RIFF\x00\x00\x00\x00WEBPC2P",
            struct.pack(">I", 4) + b"ftyp",
            b"GIF89a" + bytes(20),
            gif_bytes(c2pa=True)[:20],
        ):
            with self.subTest(data=data):
                self.assertFalse(self.detect(data))

    def test_detect_provenance(self):
        data = jpeg_bytes(xmp_packet(), c2pa=True)
        file = io.BytesIO(data)
        provenance = detect_provenance(file, PILImage.open(file))
        self.assertEqual(provenance.digital_source_type, AI_GENERATED)
        self.assertTrue(provenance.has_content_credentials)


class ProvenanceEdgeCaseTests(TestCase):
    def c2pa_segment(self):
        return jpeg_segment(0xEB, b"JP" + b"\x00\x01" + b"\x00\x00\x00\x01" + jumbf_c2pa_box())

    def test_xmp_packet_as_text(self):
        image = mock.Mock(info={"XML:com.adobe.xmp": xmp_packet().decode()})
        self.assertEqual(get_xmp_packet(image), xmp_packet().decode())
        self.assertEqual(detect_digital_source_type(image), AI_GENERATED)
        self.assertEqual(get_xmp_packet(object()), "")

    def test_unparsable_digital_source_type(self):
        xmp = b"<rdf:Description><Iptc4xmpExt:DigitalSourceType/></rdf:Description>"
        self.assertEqual(detect_digital_source_type(PILImage.open(io.BytesIO(jpeg_bytes(xmp)))), "")

    def test_insert_jpeg_xmp(self):
        data = jpeg_bytes()
        self.assertEqual(data[2:4], b"\xff\xe0")  # JFIF APP0
        app0_end = 4 + struct.unpack(">H", data[4:6])[0]
        without_app0 = data[:2] + data[app0_end:]
        for jpeg, position in ((data, app0_end), (without_app0, 2)):
            with self.subTest(position=position):
                result = insert_jpeg_xmp(jpeg, build_xmp_packet(AI_EDITED))
                self.assertEqual(result[position:position + 2], b"\xff\xe1")
                self.assertEqual(detect_digital_source_type(PILImage.open(io.BytesIO(result))), AI_EDITED)

    def test_jpeg_marker_handling(self):
        soi = b"\xff\xd8"
        for data, expected in (
            (soi + b"\x00\x00", False),  # Not a marker
            (soi + b"\xff" + self.c2pa_segment(), True),  # Fill byte
            (soi + b"\xff\xd0" + self.c2pa_segment(), True),  # Marker without payload
            (soi + b"\xff\xe0\x00\x01", False),  # Invalid segment length
            (soi + jpeg_segment(0xEB, b"JPother") + self.c2pa_segment(), True),  # Other APP11 segment
            (soi + jpeg_segment(0xEB, b"JPother") + b"\xff\xd9", False),
        ):
            with self.subTest(data=data[:8]):
                self.assertIs(detect_content_credentials(io.BytesIO(data)), expected)

    def test_isobmff_box_sizes(self):
        ftyp = isobmff_box(b"ftyp", b"avif" + bytes(4) + b"mif1avif")
        c2pa = isobmff_box(b"uuid", C2PA_ISOBMFF_UUID + jumbf_c2pa_box())
        large_box = struct.pack(">I4sQ", 1, b"free", 16 + 4) + bytes(4)
        to_end = struct.pack(">I4s", 0, b"mdat") + bytes(8)
        self.assertTrue(detect_content_credentials(io.BytesIO(ftyp + large_box + c2pa)))
        self.assertFalse(detect_content_credentials(io.BytesIO(ftyp + to_end + c2pa)))
        self.assertFalse(detect_content_credentials(io.BytesIO(ftyp + struct.pack(">I4s", 4, b"free"))))

    def test_block_limit(self):
        # Each file needs more than one block to reach its provenance information
        gif = gif_bytes(c2pa=True)
        header_size = provenance._gif_header_size(gif)
        gif = gif[:header_size] + b"!\xfe" + gif_sub_blocks(b"comment") + gif[header_size:]
        with mock.patch.object(provenance, "MAX_BLOCKS", 1):
            for data in (
                jpeg_bytes(xmp_packet(), c2pa=True),
                png_bytes(c2pa=True),
                webp_bytes(c2pa=True),
                avif_bytes(c2pa=True, other_uuid=True),
                gif,
            ):
                with self.subTest(data=data[:12]):
                    self.assertFalse(detect_content_credentials(io.BytesIO(data)))
            for data in (png_bytes_with_late_xmp(xmp_packet()), gif_bytes(xmp_packet())):
                with self.subTest(data=data[:12]):
                    self.assertEqual(read_xmp_packet(io.BytesIO(data)), b"")

    def test_detect_file_provenance(self):
        file = io.BytesIO(jpeg_bytes(xmp_packet(), c2pa=True))
        file.seek(10)
        result = detect_file_provenance(file)
        self.assertEqual(result.digital_source_type, AI_GENERATED)
        self.assertTrue(result.has_content_credentials)
        self.assertEqual(file.tell(), 0)

    def test_detect_file_provenance_is_best_effort(self):
        closed = io.BytesIO(jpeg_bytes())
        closed.close()
        for file in (io.BytesIO(b"not an image"), closed):
            with self.subTest(file=file):
                self.assertEqual(detect_file_provenance(file), provenance.Provenance())


class ContentCredentialsDigitalSourceTypeTests(TestCase):
    """The digital source type of the Content Credentials is used if the image
    has no XMP digital source type."""

    def files(self):
        return (
            jpeg_bytes(c2pa=AI_GENERATED),
            png_bytes(c2pa=AI_GENERATED),
            gif_bytes(c2pa=AI_GENERATED),
            webp_bytes(c2pa=AI_GENERATED),
            avif_bytes(c2pa=AI_GENERATED),
        )

    def test_all_formats(self):
        for data in self.files():
            with self.subTest(data=data[:12]):
                store = read_content_credentials(io.BytesIO(data))
                self.assertEqual(get_c2pa_digital_source_type(store), AI_GENERATED)

    def test_without_digital_source_type(self):
        store = read_content_credentials(io.BytesIO(jpeg_bytes(c2pa=True)))
        self.assertEqual(get_c2pa_digital_source_type(store), "")
        self.assertEqual(get_c2pa_digital_source_type(None), "")
        self.assertEqual(get_c2pa_digital_source_type(b""), "")

    def test_value_encodings(self):
        key = cbor_text("digitalSourceType")
        long_uri = "http://example.com/" + "a" * 230
        for value, expected in (
            (key + cbor_text("digitalCapture"), CAPTURE),  # Short CBOR text
            (key + cbor_text(AI_EDITED), AI_EDITED),  # One byte length
            (key + b"\x79" + struct.pack(">H", len(AI_EDITED)) + AI_EDITED.encode(), AI_EDITED),  # Two byte length
            (b'{"digitalSourceType": "%s"}' % AI_GENERATED.encode(), AI_GENERATED),  # JSON
            (key + cbor_text(long_uri), long_uri),
            (key + cbor_text("not a term"), ""),
            (key + b"\x01", ""),  # Not a text
            (key, ""),  # Truncated
            (key + b"\x79\x00", ""),
        ):
            with self.subTest(value=value[-20:]):
                self.assertEqual(get_c2pa_digital_source_type(value), expected)

    def test_generative_ai_takes_precedence(self):
        # A manifest store keeps the history of an image
        self.assertEqual(
            get_c2pa_digital_source_type(c2pa_action(AI_GENERATED) + c2pa_action(CAPTURE)), AI_GENERATED)
        self.assertEqual(
            get_c2pa_digital_source_type(c2pa_action(AI_GENERATED) + c2pa_action(AI_EDITED)), AI_EDITED)
        self.assertEqual(
            get_c2pa_digital_source_type(c2pa_action(CAPTURE) + c2pa_action("humanEdits")),
            IPTC_DIGITAL_SOURCE_TYPE_BASE + "humanEdits")

    def test_jpeg_manifest_store_split_into_segments(self):
        # A JUMBF box larger than a segment continues in the next one, which
        # repeats the box header: the value is split between them here
        box = jumbf_c2pa_box(AI_GENERATED)
        split = len(box) - 20
        header = b"JP" + b"\x00\x01"
        segments = (
            jpeg_segment(0xEB, header + struct.pack(">I", 1) + box[:split])
            + jpeg_segment(0xEB, header + struct.pack(">I", 2) + box[:8] + box[split:])
        )
        data = jpeg_bytes()
        data = data[:2] + segments + data[2:]
        store = read_content_credentials(io.BytesIO(data))
        self.assertEqual(store, box)
        self.assertEqual(get_c2pa_digital_source_type(store), AI_GENERATED)

    def test_jpeg_large_box_header_and_other_segments(self):
        box = jumbf_c2pa_box(AI_GENERATED)
        large_header = struct.pack(">I4sQ", 1, b"jumb", len(box) + 8)
        header = b"JP" + b"\x00\x01"
        segments = (
            jpeg_segment(0xEB, b"XX" + bytes(20))  # Not a JPEG XT box
            + jpeg_segment(0xEB, header + struct.pack(">I", 1) + large_header + box[8:-20])
            + jpeg_segment(0xEB, header + struct.pack(">I", 2) + large_header + box[-20:])
        )
        data = jpeg_bytes()
        store = read_content_credentials(io.BytesIO(data[:2] + segments + data[2:]))
        self.assertEqual(store, large_header + box[8:])
        self.assertEqual(get_c2pa_digital_source_type(store), AI_GENERATED)

    def test_manifest_store_size_is_limited(self):
        with mock.patch.object(provenance, "MAX_C2PA_SIZE", 10):
            for data in self.files():
                with self.subTest(data=data[:12]):
                    store = read_content_credentials(io.BytesIO(data))
                    # Still detected, but too little is read to find the value
                    self.assertIsNotNone(store)
                    self.assertLess(len(store), 300)
                    self.assertEqual(get_c2pa_digital_source_type(store[:10]), "")

    def test_isobmff_box_extending_to_end_of_file(self):
        ftyp = isobmff_box(b"ftyp", b"avif" + bytes(4) + b"mif1avif")
        payload = jumbf_c2pa_box(AI_GENERATED)
        to_end = struct.pack(">I4s", 0, b"uuid") + C2PA_ISOBMFF_UUID + payload
        self.assertEqual(read_content_credentials(io.BytesIO(ftyp + to_end)), payload)
        # A box smaller than its header has no content
        too_small = struct.pack(">I4s", 8, b"uuid") + C2PA_ISOBMFF_UUID
        self.assertEqual(read_content_credentials(io.BytesIO(ftyp + too_small)), b"")

    def test_xmp_takes_precedence(self):
        result = detect_file_provenance(io.BytesIO(jpeg_bytes(xmp_packet(CAPTURE), c2pa=AI_GENERATED)))
        self.assertEqual(result.digital_source_type, CAPTURE)
        self.assertTrue(result.has_content_credentials)

    def test_fallback(self):
        for data in self.files()[:3]:  # The formats the test images are valid for
            with self.subTest(data=data[:8]):
                result = detect_file_provenance(io.BytesIO(data))
                self.assertEqual(result.digital_source_type, AI_GENERATED)
                self.assertTrue(result.has_content_credentials)


class ImageProvenanceTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()

    def tearDown(self):
        for image in Image.objects.all():
            image.delete()

    def create(self, data, name="image.jpg"):
        return Image.objects.create(
            owner=self.superuser,
            original_filename=name,
            file=DjangoFile(io.BytesIO(data), name=name),
        )

    def test_ai_generated_image(self):
        image = self.create(jpeg_bytes(xmp_packet(), c2pa=True))
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.has_content_credentials)
        self.assertTrue(image.is_ai_generated)
        self.assertEqual(str(image.digital_source_type_label), "Created using generative AI")

    def test_camera_image(self):
        image = self.create(jpeg_bytes(xmp_packet(CAPTURE)))
        self.assertEqual(image.digital_source_type, CAPTURE)
        self.assertFalse(image.has_content_credentials)
        self.assertFalse(image.is_ai_generated)

    def test_png_with_xmp_after_image_data(self):
        image = self.create(png_bytes_with_late_xmp(xmp_packet(), compressed=True), name="late.png")
        self.assertEqual(image.digital_source_type, AI_GENERATED)

    def test_gif(self):
        image = self.create(gif_bytes(xmp_packet(), c2pa=True), name="ai.gif")
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.is_ai_generated)
        self.assertTrue(image.has_content_credentials)

    def test_image_without_provenance(self):
        image = self.create(png_bytes(), name="image.png")
        self.assertEqual(image.digital_source_type, "")
        self.assertFalse(image.has_content_credentials)
        self.assertFalse(image.is_ai_generated)

    def test_replacing_file_updates_provenance(self):
        image = self.create(jpeg_bytes(xmp_packet(), c2pa=True))
        image.file = DjangoFile(io.BytesIO(jpeg_bytes()), name="other.jpg")
        image.save()
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, "")
        self.assertFalse(image.has_content_credentials)

    def test_content_credentials_state_digital_source_type(self):
        image = self.create(jpeg_bytes(c2pa=AI_GENERATED))
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.is_ai_generated)
        self.assertFalse(image.digital_source_type_edited)

    def test_set_digital_source_type(self):
        image = self.create(jpeg_bytes())
        image.set_digital_source_type("trainedAlgorithmicMedia")
        image.save()
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.digital_source_type_edited)
        self.assertTrue(image.is_ai_generated)

        image.set_digital_source_type("")
        image.save()
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, "")
        self.assertTrue(image.digital_source_type_edited)

    def test_set_digital_source_type_keeps_file(self):
        data = jpeg_bytes(xmp_packet(), c2pa=True)
        image = self.create(data)
        image.set_digital_source_type("")
        image.save()
        image.refresh_from_db()
        self.assertTrue(image.has_content_credentials)
        with image.file.open("rb") as fh:
            self.assertEqual(fh.read(), data)

    def test_replacing_file_replaces_edited_digital_source_type(self):
        image = self.create(jpeg_bytes())
        image.set_digital_source_type(AI_GENERATED)
        image.save()
        image.file = DjangoFile(io.BytesIO(jpeg_bytes(xmp_packet(CAPTURE))), name="other.jpg")
        image.save()
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, CAPTURE)
        self.assertFalse(image.digital_source_type_edited)

    def test_deferred_digital_source_type_is_not_loaded(self):
        self.create(jpeg_bytes(xmp_packet()))
        with self.assertNumQueries(1):
            image = Image.objects.defer("digital_source_type").get()
            self.assertIsNone(image._old_digital_source_type)
            self.assertNotIn("digital_source_type", image.__dict__)

    def test_detection_does_not_consume_file(self):
        # Upload validators read the same file object after the model did
        data = jpeg_bytes(xmp_packet(), c2pa=True)
        file = DjangoFile(io.BytesIO(data), name="image.jpg")
        Image(owner=self.superuser, original_filename="image.jpg", file=file)
        self.assertEqual(file.file.tell(), 0)


class ImageProvenanceAdminTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username="admin", password="secret")
        self.folder = Folder.objects.create(name="foo")

    def tearDown(self):
        self.client.logout()
        for image in Image.objects.all():
            image.delete()

    def upload(self, data, name="ai.jpg"):
        url = reverse("admin:filer-ajax_upload", kwargs={"folder_id": self.folder.pk})
        response = self.client.post(url, {"file": SimpleUploadedFile(name, data, content_type="image/jpeg")})
        self.assertEqual(response.status_code, 200, response.content)
        return Image.objects.get(original_filename=name)

    def test_upload_detects_provenance(self):
        image = self.upload(jpeg_bytes(xmp_packet(), c2pa=True))
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.has_content_credentials)

    def test_upload_keeps_original_metadata(self):
        data = jpeg_bytes(xmp_packet(), c2pa=True)
        image = self.upload(data)
        with image.file.open("rb") as fh:
            self.assertEqual(fh.read(), data)

    def test_change_view_shows_provenance(self):
        image = self.upload(jpeg_bytes(xmp_packet(), c2pa=True))
        response = self.client.get(reverse(
            f"admin:{Image._meta.app_label}_{Image._meta.model_name}_change", args=(image.pk,)
        ))
        self.assertContains(response, "Created using generative AI")
        self.assertContains(response, "C2PA manifest found on upload (not verified)")

    def test_change_view_without_provenance(self):
        image = self.upload(jpeg_bytes(), name="plain.jpg")
        response = self.client.get(reverse(
            f"admin:{Image._meta.app_label}_{Image._meta.model_name}_change", args=(image.pk,)
        ))
        self.assertNotContains(response, "Content Credentials")

    def test_directory_listing_shows_ai_label(self):
        self.upload(jpeg_bytes(xmp_packet(AI_EDITED)))
        self.upload(jpeg_bytes(xmp_packet(CAPTURE)), name="photo.jpg")
        url = reverse("admin:filer-directory_listing", kwargs={"folder_id": self.folder.pk})
        label = (
            '<img class="filer-ai-label" src="/static/filer/icons/ai-label.svg" alt="AI" '
            'title="Edited using generative AI" width="20" height="20">'
        )
        for list_type in ("tb", "th"):
            with self.subTest(list_type=list_type):
                response = self.client.get(url, {"_list_type": list_type})
                self.assertContains(response, label, count=1, html=True)
                self.assertNotContains(response, 'title="Original digital capture"')

    def change(self, image, **data):
        url = reverse(f"admin:{Image._meta.app_label}_{Image._meta.model_name}_change", args=(image.pk,))
        response = self.client.post(url, {
            "name": image.name or "",
            "owner": self.superuser.pk,
            "description": "",
            "subject_location": "",
            "_continue": "1",
            **data,
        })
        self.assertEqual(response.status_code, 302, response.content[-2000:])
        image.refresh_from_db()
        return image

    def test_change_form_offers_digital_source_types(self):
        image = self.upload(jpeg_bytes(xmp_packet()))
        response = self.client.get(reverse(
            f"admin:{Image._meta.app_label}_{Image._meta.model_name}_change", args=(image.pk,)
        ))
        self.assertContains(
            response, f'<option value="{AI_GENERATED}" selected>Created using generative AI</option>', html=True)
        self.assertContains(response, '<option value="">Not specified</option>', html=True)

    def test_ai_digital_source_types_setting(self):
        synthetic = IPTC_DIGITAL_SOURCE_TYPE_BASE + "compositeSynthetic"
        image = self.upload(jpeg_bytes(xmp_packet(synthetic)), name="synthetic.jpg")
        self.upload(jpeg_bytes(xmp_packet()))
        url = reverse("admin:filer-directory_listing", kwargs={"folder_id": self.folder.pk})
        self.assertFalse(image.is_ai_generated)
        self.assertEqual(Image.objects.filter(provenance.ai_digital_source_type_q()).count(), 1)
        self.assertContains(self.client.get(url), 'class="filer-ai-label"', count=1)

        # Terms or URIs
        types = ("trainedAlgorithmicMedia", synthetic, "")
        with mock.patch.object(filer_settings, "FILER_AI_DIGITAL_SOURCE_TYPES", types):
            self.assertTrue(image.is_ai_generated)
            self.assertEqual(Image.objects.filter(provenance.ai_digital_source_type_q()).count(), 2)
            self.assertContains(self.client.get(url), 'class="filer-ai-label"', count=2)

        with mock.patch.object(filer_settings, "FILER_AI_DIGITAL_SOURCE_TYPES", ()):
            self.assertFalse(image.is_ai_generated)
            self.assertEqual(Image.objects.filter(provenance.ai_digital_source_type_q()).count(), 0)

    def test_change_form_offers_generative_ai_by_default(self):
        self.assertEqual(
            [value for value, _label in get_digital_source_type_choices()], ["", AI_GENERATED, AI_EDITED])
        choices = ("digitalCapture", CAPTURE, "not a term", AI_EDITED)
        with mock.patch.object(filer_settings, "FILER_DIGITAL_SOURCE_TYPE_CHOICES", choices):
            self.assertEqual(
                [value for value, _label in get_digital_source_type_choices()], ["", CAPTURE, AI_EDITED])

    def test_change_form_keeps_other_digital_source_type(self):
        # A detected digital source type that is not offered stays as it is
        image = self.upload(jpeg_bytes(xmp_packet(CAPTURE)), name="photo.jpg")
        response = self.client.get(reverse(
            f"admin:{Image._meta.app_label}_{Image._meta.model_name}_change", args=(image.pk,)
        ))
        self.assertContains(
            response, f'<option value="{CAPTURE}" selected>Original digital capture</option>', html=True)
        self.assertNotContains(response, "Screen capture")
        image = self.change(image, name="Photo", digital_source_type=CAPTURE)
        self.assertEqual(image.digital_source_type, CAPTURE)
        self.assertFalse(image.digital_source_type_edited)

    def test_change_form_sets_digital_source_type(self):
        image = self.upload(jpeg_bytes(), name="plain.jpg")
        image = self.change(image, digital_source_type=AI_GENERATED)
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.digital_source_type_edited)
        self.assertTrue(image.is_ai_generated)

    def test_change_form_unsets_digital_source_type(self):
        data = jpeg_bytes(xmp_packet(), c2pa=True)
        image = self.upload(data)
        image = self.change(image, digital_source_type="")
        self.assertEqual(image.digital_source_type, "")
        self.assertTrue(image.digital_source_type_edited)
        # Neither the file nor what is known about its Content Credentials changed
        self.assertTrue(image.has_content_credentials)
        with image.file.open("rb") as fh:
            self.assertEqual(fh.read(), data)

    def test_change_form_without_change_is_no_edit(self):
        image = self.upload(jpeg_bytes(xmp_packet()))
        image = self.change(image, name="Renamed", digital_source_type=AI_GENERATED)
        self.assertEqual(image.name, "Renamed")
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertFalse(image.digital_source_type_edited)

    def test_change_form_rejects_unknown_digital_source_type(self):
        image = self.upload(jpeg_bytes(), name="plain.jpg")
        url = reverse(f"admin:{Image._meta.app_label}_{Image._meta.model_name}_change", args=(image.pk,))
        response = self.client.post(url, {
            "name": "", "owner": self.superuser.pk, "description": "", "subject_location": "",
            "digital_source_type": "javascript:alert(1)",
        })
        self.assertEqual(response.status_code, 200)
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, "")

    def test_change_form_keeps_digital_source_type_outside_vocabulary(self):
        custom = "http://example.com/vocabulary/custom"
        image = self.upload(jpeg_bytes(xmp_packet(custom)))
        self.assertIn((custom, "custom"), get_digital_source_type_choices(custom))
        image = self.change(image, digital_source_type=custom)
        self.assertEqual(image.digital_source_type, custom)
        self.assertFalse(image.digital_source_type_edited)

    def test_change_form_new_file_replaces_digital_source_type(self):
        image = self.upload(jpeg_bytes(), name="plain.jpg")
        image = self.change(image, digital_source_type=AI_GENERATED)
        image = self.change(
            image,
            digital_source_type=AI_GENERATED,
            file=SimpleUploadedFile("photo.jpg", jpeg_bytes(xmp_packet(CAPTURE)), content_type="image/jpeg"),
        )
        self.assertEqual(image.digital_source_type, CAPTURE)
        self.assertFalse(image.digital_source_type_edited)

    def test_change_form_choice_wins_over_new_file(self):
        image = self.upload(jpeg_bytes(), name="plain.jpg")
        image = self.change(
            image,
            digital_source_type=AI_EDITED,
            file=SimpleUploadedFile("photo.jpg", jpeg_bytes(xmp_packet(CAPTURE)), content_type="image/jpeg"),
        )
        self.assertEqual(image.digital_source_type, AI_EDITED)
        self.assertTrue(image.digital_source_type_edited)



def exif_bytes():
    exif = PILImage.Exif()
    exif[0x010F] = "Camera maker"  # Make
    return exif.tobytes()


class StripExifProvenanceTests(TestCase):
    def strip(self, data, name, mime_type):
        buffer = io.BytesIO(data)
        strip_exif(name, buffer, None, mime_type)
        return buffer.getvalue()

    def test_jpeg_keeps_digital_source_type(self):
        data = jpeg_bytes(xmp_packet(form="element") + b"<!-- Creator: Jane Doe -->")
        image = PILImage.open(io.BytesIO(data))
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", exif=exif_bytes())
        data = buffer.getvalue()[:2] + data[2:data.index(b"\xff\xdb")] + buffer.getvalue()[2:]

        stripped = self.strip(data, "ai.jpg", "image/jpeg")

        result = PILImage.open(io.BytesIO(stripped))
        self.assertEqual(detect_digital_source_type(result), AI_GENERATED)
        self.assertFalse(result.getexif())
        self.assertNotIn(b"Jane Doe", stripped)
        self.assertNotIn(b"Camera maker", stripped)

    def test_png_keeps_digital_source_type(self):
        stripped = self.strip(png_bytes(xmp_packet(AI_EDITED)), "ai.png", "image/png")
        self.assertEqual(detect_digital_source_type(PILImage.open(io.BytesIO(stripped))), AI_EDITED)

    def test_png_keeps_digital_source_type_after_image_data(self):
        stripped = self.strip(png_bytes_with_late_xmp(xmp_packet()), "ai.png", "image/png")
        file = io.BytesIO(stripped)
        self.assertEqual(detect_digital_source_type(PILImage.open(file), file), AI_GENERATED)

    def test_webp_keeps_digital_source_type(self):
        buffer = io.BytesIO()
        create_image(size=(40, 30)).save(buffer, "WEBP", xmp=xmp_packet(), exif=exif_bytes())
        stripped = self.strip(buffer.getvalue(), "ai.webp", "image/webp")
        result = PILImage.open(io.BytesIO(stripped))
        self.assertEqual(detect_digital_source_type(result), AI_GENERATED)
        self.assertNotIn(b"Camera maker", stripped)

    def test_gif_keeps_digital_source_type(self):
        data = gif_bytes(xmp_packet(form="element") + b"<!-- Creator: Jane Doe -->", c2pa=True, comment=b"Jane")
        stripped = self.strip(data, "ai.gif", "image/gif")
        file = io.BytesIO(stripped)
        result = PILImage.open(file)
        self.assertEqual(detect_digital_source_type(result, file), AI_GENERATED)
        self.assertFalse(detect_content_credentials(io.BytesIO(stripped)))
        self.assertNotIn(b"Jane", stripped)
        self.assertNotIn("comment", result.info)
        self.assertEqual(result.size, (40, 30))

    def test_gif_setting_disables_keeping_digital_source_type(self):
        with mock.patch.object(filer_settings, "FILER_STRIP_EXIF_KEEP_DIGITAL_SOURCE_TYPE", False):
            stripped = self.strip(gif_bytes(xmp_packet()), "ai.gif", "image/gif")
        self.assertNotIn(b"DigitalSourceType", stripped)
        self.assertNotIn(b"XMP DataXMP", stripped)

    def frames(self, data):
        image = PILImage.open(io.BytesIO(data))
        frames = []
        for frame in range(image.n_frames):
            image.seek(frame)
            image.load()
            frames.append((
                image.info.get("duration"),
                getattr(image, "disposal_method", None),
                image.convert("RGB").getpixel((frame * 5, 0)),
            ))
        image.seek(0)
        return frames, image.info.get("loop")

    def animation(self, mode):
        frames = []
        for frame in range(3):
            image = PILImage.new("RGB", (20, 20), (255, 255, 255))
            PILImageDraw.Draw(image).rectangle((frame * 5, 0, frame * 5 + 4, 19), (255, 0, 0))
            frames.append(image.convert(mode))
        return frames

    def test_animated_gif_keeps_frames(self):
        frames = self.animation("P")
        for loop in ({"loop": 2}, {}):
            with self.subTest(loop=loop):
                buffer = io.BytesIO()
                frames[0].save(
                    buffer, "GIF", save_all=True, append_images=frames[1:], duration=[100, 200, 300],
                    disposal=[2, 1, 2], comment=b"secret", **loop,
                )
                stripped = self.strip(buffer.getvalue(), "anim.gif", "image/gif")
                self.assertNotIn(b"secret", stripped)
                self.assertEqual(self.frames(stripped), self.frames(buffer.getvalue()))

    def test_animated_webp_keeps_frames(self):
        frames = self.animation("RGB")
        buffer = io.BytesIO()
        frames[0].save(
            buffer, "WEBP", save_all=True, append_images=frames[1:], duration=[100, 200, 300], loop=2,
            lossless=True, exif=exif_bytes(),
        )
        stripped = self.strip(buffer.getvalue(), "anim.webp", "image/webp")
        self.assertNotIn(b"Camera maker", stripped)
        self.assertEqual(self.frames(stripped), self.frames(buffer.getvalue()))

    def test_c2pa_is_removed(self):
        stripped = self.strip(jpeg_bytes(xmp_packet(), c2pa=True), "ai.jpg", "image/jpeg")
        self.assertFalse(detect_content_credentials(io.BytesIO(stripped)))
        self.assertEqual(detect_digital_source_type(PILImage.open(io.BytesIO(stripped))), AI_GENERATED)

    def test_digital_source_type_of_content_credentials_is_kept(self):
        # Without XMP, the removed Content Credentials are the only statement
        stripped = self.strip(jpeg_bytes(c2pa=AI_GENERATED), "ai.jpg", "image/jpeg")
        self.assertFalse(detect_content_credentials(io.BytesIO(stripped)))
        self.assertEqual(detect_digital_source_type(PILImage.open(io.BytesIO(stripped))), AI_GENERATED)

    def test_setting_disables_keeping_digital_source_type(self):
        with mock.patch.object(filer_settings, "FILER_STRIP_EXIF_KEEP_DIGITAL_SOURCE_TYPE", False):
            stripped = self.strip(jpeg_bytes(xmp_packet()), "ai.jpg", "image/jpeg")
        self.assertNotIn(b"DigitalSourceType", stripped)

    def test_without_digital_source_type_no_xmp_is_added(self):
        stripped = self.strip(jpeg_bytes(b'<x:xmpmeta xmlns:x="adobe:ns:meta/"/>'), "plain.jpg", "image/jpeg")
        self.assertNotIn(b"http://ns.adobe.com/xap/1.0/", stripped)


class StripExifUploadTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username="admin", password="secret")
        self.folder = Folder.objects.create(name="foo")
        config = apps.get_app_config("filer")
        patcher = mock.patch.dict(config.FILE_VALIDATORS, {"image/jpeg": [strip_exif]})
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.client.logout()
        for image in Image.objects.all():
            image.delete()

    def test_clipboard_upload(self):
        url = reverse("admin:filer-ajax_upload", kwargs={"folder_id": self.folder.pk})
        data = jpeg_bytes(xmp_packet(), c2pa=True)
        response = self.client.post(url, {"file": SimpleUploadedFile("ai.jpg", data, content_type="image/jpeg")})
        self.assertEqual(response.status_code, 200, response.content)

        image = Image.objects.get()
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.has_content_credentials)
        with image.file.open("rb") as fh:
            stored = fh.read()
        self.assertNotEqual(stored, data)
        self.assertFalse(detect_content_credentials(io.BytesIO(stored)))

    def test_change_form_upload(self):
        image = Image.objects.create(
            owner=self.superuser,
            original_filename="plain.jpg",
            folder=self.folder,
            file=DjangoFile(io.BytesIO(jpeg_bytes()), name="plain.jpg"),
        )
        url = reverse(f"admin:{Image._meta.app_label}_{Image._meta.model_name}_change", args=(image.pk,))
        response = self.client.post(url, {
            "name": "AI image",
            "owner": self.superuser.pk,
            "description": "",
            "subject_location": "",
            "file": SimpleUploadedFile("ai.jpg", jpeg_bytes(xmp_packet(), c2pa=True), content_type="image/jpeg"),
            "_continue": "1",
        })
        self.assertEqual(response.status_code, 302, response.content[-2000:])

        image.refresh_from_db()
        self.assertEqual(image.name, "AI image")
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.has_content_credentials)
        with image.file.open("rb") as fh:
            self.assertFalse(detect_content_credentials(fh))


class ThumbnailProvenanceTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()

    def tearDown(self):
        for image in Image.objects.all():
            image.file.delete_thumbnails()
            image.delete()

    def create(self, data, name="image.jpg"):
        return Image.objects.create(
            owner=self.superuser,
            original_filename=name,
            file=DjangoFile(io.BytesIO(data), name=name),
        )

    def read(self, thumbnail):
        with thumbnail.storage.open(thumbnail.name, "rb") as fh:
            return fh.read()

    def detect(self, data):
        file = io.BytesIO(data)
        return detect_digital_source_type(PILImage.open(file), file)

    def test_thumbnailers_keep_digital_source_type(self):
        image = self.create(jpeg_bytes(xmp_packet(AI_EDITED), c2pa=True))
        # Different sizes, so that each thumbnailer generates its own thumbnail
        for name, thumbnailer, width in (
            ("field file", image.file, 20),
            ("model", get_thumbnailer(image), 24),
        ):
            with self.subTest(name):
                thumbnail = thumbnailer.get_thumbnail({"size": (width, width)}, generate=True)
                data = self.read(thumbnail)
                self.assertTrue(thumbnail.name.endswith(".jpg"))
                self.assertEqual(self.detect(data), AI_EDITED)
                self.assertFalse(detect_content_credentials(io.BytesIO(data)))
                self.assertEqual(PILImage.open(io.BytesIO(data)).size[0], width)

    def test_changed_digital_source_type_regenerates_thumbnails(self):
        image = self.create(jpeg_bytes(xmp_packet()))
        options = {"size": (20, 20)}
        thumbnail = image.file.get_thumbnail(options, generate=True)
        self.assertEqual(self.detect(self.read(thumbnail)), AI_GENERATED)

        image.set_digital_source_type("")
        image.save()
        self.assertFalse(thumbnail.storage.exists(thumbnail.name))
        self.assertEqual(self.detect(self.read(image.file.get_thumbnail(options, generate=True))), "")

        image = Image.objects.get(pk=image.pk)
        image.set_digital_source_type(AI_EDITED)
        image.save()
        self.assertEqual(self.detect(self.read(image.file.get_thumbnail(options, generate=True))), AI_EDITED)

    def test_unchanged_digital_source_type_keeps_thumbnails(self):
        image = self.create(jpeg_bytes(xmp_packet()))
        thumbnail = image.file.get_thumbnail({"size": (20, 20)}, generate=True)
        image = Image.objects.get(pk=image.pk)
        image.name = "Renamed"
        image.save()
        self.assertTrue(thumbnail.storage.exists(thumbnail.name))

    def test_failing_thumbnail_deletion_does_not_fail_save(self):
        image = self.create(jpeg_bytes(xmp_packet()))
        image.set_digital_source_type("")
        with mock.patch.object(type(image.file), "delete_thumbnails", side_effect=OSError), \
                self.assertLogs("filer.models.abstract", "WARNING"):
            image.save()
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, "")

    def test_admin_icons_keep_digital_source_type(self):
        image = self.create(jpeg_bytes(xmp_packet()))
        self.assertTrue(image.icons)
        for thumbnail in image.file.get_thumbnails():
            self.assertEqual(self.detect(self.read(thumbnail)), AI_GENERATED)

    def test_transparent_png(self):
        buffer = io.BytesIO()
        create_image(mode="RGBA", size=(40, 30)).save(buffer, "PNG")
        image = self.create(buffer.getvalue(), name="ai.png")
        # The upload had no XMP; the digital source type in the database counts
        Image.objects.filter(pk=image.pk).update(digital_source_type=AI_GENERATED)
        image.refresh_from_db()
        thumbnail = image.file.get_thumbnail({"size": (20, 20)}, generate=True)
        self.assertTrue(thumbnail.name.endswith(".png"))
        self.assertEqual(self.detect(self.read(thumbnail)), AI_GENERATED)

    def test_webp(self):
        buffer = io.BytesIO()
        create_image(size=(40, 30)).save(buffer, "WEBP", xmp=xmp_packet())
        image = self.create(buffer.getvalue(), name="ai.webp")
        with override_settings(THUMBNAIL_PRESERVE_EXTENSIONS=("webp",)):
            # The thumbnailer reads the setting when it is created
            thumbnail = Image.objects.get(pk=image.pk).file.get_thumbnail({"size": (20, 20)}, generate=True)
        self.assertTrue(thumbnail.name.endswith(".webp"))
        data = self.read(thumbnail)
        self.assertEqual(self.detect(data), AI_GENERATED)
        self.assertEqual(PILImage.open(io.BytesIO(data)).size, (20, 15))

    def test_gif(self):
        image = self.create(gif_bytes(xmp_packet()), name="ai.gif")
        with override_settings(THUMBNAIL_PRESERVE_EXTENSIONS=("gif",)):
            # The thumbnailer reads the setting when it is created
            thumbnail = Image.objects.get(pk=image.pk).file.get_thumbnail({"size": (20, 20)}, generate=True)
        self.assertTrue(thumbnail.name.endswith(".gif"))
        self.assertEqual(self.detect(self.read(thumbnail)), AI_GENERATED)

    def test_without_digital_source_type_no_xmp_is_added(self):
        image = self.create(jpeg_bytes())
        data = self.read(image.file.get_thumbnail({"size": (20, 20)}, generate=True))
        self.assertNotIn(b"http://ns.adobe.com/xap/1.0/", data)

    def test_failure_keeps_thumbnail(self):
        image = self.create(jpeg_bytes(xmp_packet()))
        with mock.patch("filer.utils.filer_easy_thumbnails.embed_xmp", side_effect=ValueError), \
                self.assertLogs("filer.utils.filer_easy_thumbnails", "WARNING"):
            thumbnail = image.file.get_thumbnail({"size": (20, 20)}, generate=True)
        self.assertEqual(PILImage.open(io.BytesIO(self.read(thumbnail))).size, (20, 15))

    def test_embed_xmp(self):
        xmp = build_xmp_packet(AI_GENERATED)
        for image_format, data in (
            ("JPEG", jpeg_bytes()),
            ("PNG", png_bytes()),
            ("GIF", gif_bytes()),
        ):
            with self.subTest(image_format):
                result = embed_xmp(data, image_format, xmp)
                self.assertEqual(self.detect(result), AI_GENERATED)
                PILImage.open(io.BytesIO(result)).load()
        self.assertIsNone(embed_xmp(b"", "WEBP", xmp))


class ResizeProvenanceTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username="admin", password="secret")
        self.folder = Folder.objects.create(name="foo")

    def tearDown(self):
        self.client.logout()
        for image in Image.objects.all():
            image.delete()

    def resize(self, data, name):
        image = Image.objects.create(
            owner=self.superuser,
            original_filename=name,
            folder=self.folder,
            file=DjangoFile(io.BytesIO(data), name=name),
        )
        response = self.client.post(
            reverse("admin:filer-directory_listing", kwargs={"folder_id": self.folder.pk}),
            {
                "action": "resize_images",
                "post": "yes",
                "width": 20,
                "height": 20,
                "crop": False,
                "upscale": False,
                helpers.ACTION_CHECKBOX_NAME: f"file-{image.pk}",
            },
        )
        self.assertEqual(response.status_code, 302)
        image.refresh_from_db()
        with image.file.open("rb") as fh:
            return image, fh.read()

    def test_resized_original_keeps_digital_source_type(self):
        image, data = self.resize(jpeg_bytes(xmp_packet(), c2pa=True), "ai.jpg")
        self.assertEqual((image.width, image.height), (20, 15))
        file = io.BytesIO(data)
        self.assertEqual(detect_digital_source_type(PILImage.open(file), file), AI_GENERATED)
        # The Content Credentials cannot survive, but the database still
        # records that the upload had them
        self.assertFalse(detect_content_credentials(io.BytesIO(data)))
        self.assertEqual(image.digital_source_type, AI_GENERATED)
        self.assertTrue(image.has_content_credentials)

    def test_resized_png(self):
        image, data = self.resize(png_bytes(xmp_packet(AI_EDITED)), "ai.png")
        self.assertEqual((image.width, image.height), (20, 15))
        self.assertEqual(detect_digital_source_type(PILImage.open(io.BytesIO(data))), AI_EDITED)
        self.assertEqual(image.digital_source_type, AI_EDITED)

    def test_resized_image_without_digital_source_type(self):
        image, data = self.resize(jpeg_bytes(), "plain.jpg")
        self.assertNotIn(b"http://ns.adobe.com/xap/1.0/", data)
        self.assertEqual(image.digital_source_type, "")


class DetectProvenanceCommandTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()

    def tearDown(self):
        for image in Image.objects.all():
            image.delete()

    def create(self, data, name="image.jpg"):
        image = Image.objects.create(
            owner=self.superuser,
            original_filename=name,
            file=DjangoFile(io.BytesIO(data), name=name),
        )
        # Simulate an image uploaded before provenance was detected
        Image.objects.filter(pk=image.pk).update(digital_source_type="", has_content_credentials=False)
        return image

    def call(self, *args):
        out = io.StringIO()
        call_command("filer_detect_provenance", *args, stdout=out, stderr=io.StringIO())
        return out.getvalue()

    def test_backfill(self):
        ai = self.create(jpeg_bytes(xmp_packet(), c2pa=True), "ai.jpg")
        plain = self.create(jpeg_bytes(), "plain.jpg")

        output = self.call()

        self.assertIn("Scanned 2 images, updated 1, failed 0.", output)
        ai.refresh_from_db()
        plain.refresh_from_db()
        self.assertEqual(ai.digital_source_type, AI_GENERATED)
        self.assertTrue(ai.has_content_credentials)
        self.assertEqual(plain.digital_source_type, "")
        self.assertFalse(plain.has_content_credentials)

    def test_dry_run(self):
        ai = self.create(jpeg_bytes(xmp_packet()), "ai.jpg")
        output = self.call("--dry-run")
        self.assertIn("would update 1", output)
        ai.refresh_from_db()
        self.assertEqual(ai.digital_source_type, "")

    def test_does_not_clear_information(self):
        # The stored file lost its Content Credentials, e.g. to strip_exif
        image = self.create(jpeg_bytes(), "stripped.jpg")
        Image.objects.filter(pk=image.pk).update(has_content_credentials=True)
        self.call()
        image.refresh_from_db()
        self.assertTrue(image.has_content_credentials)

    def test_keeps_digital_source_type_removed_by_user(self):
        image = self.create(jpeg_bytes(xmp_packet(), c2pa=True), "ai.jpg")
        Image.objects.filter(pk=image.pk).update(digital_source_type_edited=True)
        self.call()
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, "")
        # ... but still completes the other information
        self.assertTrue(image.has_content_credentials)

        self.assertIn("Scanned 0 images", self.call())

    def test_backfill_from_content_credentials(self):
        image = self.create(jpeg_bytes(c2pa=AI_EDITED), "ai.jpg")
        self.call()
        image.refresh_from_db()
        self.assertEqual(image.digital_source_type, AI_EDITED)

    def test_missing_file(self):
        image = self.create(jpeg_bytes(), "gone.jpg")
        image.file.storage.delete(image.file.name)
        self.assertIn("failed 1", self.call())


class ProvenanceFilterTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username="admin", password="secret")
        self.folder = Folder.objects.create(name="foo")
        self.subfolder = Folder.objects.create(name="bar", parent=self.folder)
        self.create(jpeg_bytes(xmp_packet()), "generated.jpg", self.folder)
        self.create(jpeg_bytes(xmp_packet(AI_EDITED)), "edited.jpg", self.subfolder)
        self.create(jpeg_bytes(xmp_packet(CAPTURE), c2pa=True), "credentials.jpg", self.folder)
        self.create(jpeg_bytes(), "plain.jpg", self.folder)

    def tearDown(self):
        self.client.logout()
        for image in Image.objects.all():
            image.delete()

    def create(self, data, name, folder):
        return Image.objects.create(
            owner=self.superuser,
            original_filename=name,
            folder=folder,
            file=DjangoFile(io.BytesIO(data), name=name),
        )

    def listing(self, folder=None, **params):
        if folder is None:
            url = reverse("admin:filer-directory_listing-root")
        else:
            url = reverse("admin:filer-directory_listing", kwargs={"folder_id": folder.pk})
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200)
        return {item.original_filename for item in response.context["paginated_items"].object_list
                if hasattr(item, "original_filename")}, response

    def test_ai_filter_searches_all_folders(self):
        names, response = self.listing(self.folder, provenance="ai")
        self.assertEqual(names, {"generated.jpg", "edited.jpg"})
        self.assertEqual(response.context["provenance_filter"], "ai")
        self.assertTrue(response.context["show_result_count"])

    def test_ai_filter_limited_to_folder(self):
        names, _response = self.listing(self.subfolder, provenance="ai", limit_search_to_folder="on")
        self.assertEqual(names, {"edited.jpg"})

    def test_specific_digital_source_type_filter(self):
        names, response = self.listing(provenance="trainedAlgorithmicMedia")
        self.assertEqual(names, {"generated.jpg"})
        self.assertEqual(response.context["provenance_filter"], "trainedAlgorithmicMedia")
        names, _response = self.listing(provenance="compositeWithTrainedAlgorithmicMedia")
        self.assertEqual(names, {"edited.jpg"})

    def test_only_offered_digital_source_types_are_filters(self):
        # By default, those denoting generative AI
        names, response = self.listing(self.folder, provenance="digitalCapture")
        self.assertEqual(names, {"generated.jpg", "credentials.jpg", "plain.jpg"})
        self.assertEqual(response.context["provenance_filter"], "")
        self.assertNotContains(response, '<option value="digitalCapture">')

        choices = ("digitalCapture", IPTC_DIGITAL_SOURCE_TYPE_BASE + "screenCapture", "not a term")
        with mock.patch.object(filer_settings, "FILER_DIGITAL_SOURCE_TYPE_CHOICES", choices):
            names, response = self.listing(provenance="digitalCapture")
            self.assertEqual(names, {"credentials.jpg"})
            self.assertContains(
                response, '<option value="digitalCapture" selected>Original digital capture</option>', html=True)
            self.assertNotContains(response, '<option value="trainedAlgorithmicMedia">')
            names, _response = self.listing(provenance="screenCapture")
            self.assertEqual(names, set())

    def test_filter_follows_edited_digital_source_type(self):
        image = Image.objects.get(original_filename="plain.jpg")
        image.set_digital_source_type("trainedAlgorithmicMedia")
        image.save()
        image = Image.objects.get(original_filename="edited.jpg")
        image.set_digital_source_type("")
        image.save()
        names, _response = self.listing(provenance="ai")
        self.assertEqual(names, {"generated.jpg", "plain.jpg"})

    def test_content_credentials_are_no_filter(self):
        names, response = self.listing(self.folder, provenance="content_credentials")
        self.assertEqual(names, {"generated.jpg", "credentials.jpg", "plain.jpg"})
        self.assertEqual(response.context["provenance_filter"], "")

    def test_filter_combined_with_search(self):
        names, _response = self.listing(provenance="ai", q="edited")
        self.assertEqual(names, {"edited.jpg"})

    def test_unknown_filter_is_ignored(self):
        names, response = self.listing(self.folder, provenance="bogus")
        self.assertEqual(names, {"generated.jpg", "credentials.jpg", "plain.jpg"})
        self.assertEqual(response.context["provenance_filter"], "")

    def test_filter_options_are_rendered(self):
        _names, response = self.listing(self.folder, provenance="ai")
        self.assertContains(response, '<select name="provenance" id="provenance_filter">')
        self.assertContains(
            response, '<option value="ai" selected>Created or edited using generative AI</option>', html=True)
        self.assertContains(
            response, '<option value="trainedAlgorithmicMedia">Created using generative AI</option>', html=True)
