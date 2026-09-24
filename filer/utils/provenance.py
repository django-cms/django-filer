"""
Detection of provenance information embedded in uploaded images.

Two standards mark an image as created or edited by generative AI:

* The IPTC ``DigitalSourceType`` property, stored in the image's XMP packet
  (see https://cv.iptc.org/newscodes/digitalsourcetype/).
* C2PA Content Credentials, a signed manifest store embedded in the file
  (see https://spec.c2pa.org/).

Only the *presence* of a C2PA manifest store is detected here. Its signature is
not validated, so its claims must not be treated as verified.

All functions are best effort: malformed files never raise, they simply yield
no provenance information.
"""
import re
import struct
import zlib
from dataclasses import dataclass
from xml.sax.saxutils import quoteattr

from django.db.models import Q
from django.utils.translation import gettext_lazy as _


IPTC_DIGITAL_SOURCE_TYPE_BASE = "http://cv.iptc.org/newscodes/digitalsourcetype/"

# IPTC digital source types denoting content created or edited by generative AI
AI_DIGITAL_SOURCE_TYPES = frozenset((
    "trainedAlgorithmicMedia",
    "compositeWithTrainedAlgorithmicMedia",
))

DIGITAL_SOURCE_TYPE_LABELS = {
    "digitalCapture": _("Original digital capture"),
    "negativeFilm": _("Digitised from a negative"),
    "positiveFilm": _("Digitised from a transparency"),
    "print": _("Digitised from a print"),
    "minorHumanEdits": _("Original media with minor human edits"),
    "humanEdits": _("Edited media"),
    "compositeCapture": _("Composite of captured elements"),
    "algorithmicallyEnhanced": _("Algorithmically enhanced media"),
    "dataDrivenMedia": _("Data-driven media"),
    "digitalArt": _("Digital art"),
    "digitalCreation": _("Digital creation"),
    "virtualRecording": _("Virtual recording"),
    "compositeSynthetic": _("Composite of synthetic elements"),
    "trainedAlgorithmicMedia": _("Created using generative AI"),
    "compositeWithTrainedAlgorithmicMedia": _("Edited using generative AI"),
    "algorithmicMedia": _("Purely algorithmic media"),
    "screenCapture": _("Screen capture"),
}

# Upper bound for the XMP packet searched and for the stored URI
MAX_XMP_SIZE = 2 * 1024 * 1024
MAX_DIGITAL_SOURCE_TYPE_LENGTH = 255

# Pillow exposes the XMP packet under different keys depending on the format
XMP_INFO_KEYS = ("xmp", "XML:com.adobe.xmp")
JPEG_XMP_IDENTIFIER = b"http://ns.adobe.com/xap/1.0/\x00"
PNG_XMP_KEYWORD = b"XML:com.adobe.xmp\x00"
GIF_XMP_IDENTIFIER = b"XMP DataXMP"
# GIF stores the XMP packet as raw bytes followed by a "magic trailer" that lets
# GIF readers skip it as a sequence of sub-blocks: 0x01, 0xFF, 0xFE, ..., 0x00
GIF_XMP_TRAILER = b"\x01\xff\xfe\xfd"
GIF_XMP_MAGIC_TRAILER = b"\x01" + bytes(range(255, -1, -1)) + b"\x00"

# The property may be serialized as an attribute, as an rdf:resource reference
# or as element text. The namespace prefix is not fixed by the XMP standard.
_DIGITAL_SOURCE_TYPE_PATTERNS = (
    re.compile(r"<[\w.-]+:DigitalSourceType\s[^>]*?rdf:resource\s*=\s*([\"'])(.*?)\1", re.DOTALL),
    re.compile(r"[\w.-]+:DigitalSourceType\s*=\s*([\"'])(.*?)\1", re.DOTALL),
    re.compile(r"<[\w.-]+:DigitalSourceType(?:\s[^>]*)?>()\s*([^<]*?)\s*</", re.DOTALL),
)

# C2PA manifest stores are embedded in a format-specific container
C2PA_ISOBMFF_UUID = bytes.fromhex("d8fec3d61b0e483c92975828877ec481")
C2PA_JUMBF_LABEL = b"c2pa"
C2PA_GIF_IDENTIFIER = b"C2PA_GIF"

# Safety limit for the number of segments, chunks or boxes walked per file
MAX_BLOCKS = 10000


@dataclass(frozen=True)
class Provenance:
    digital_source_type: str = ""
    has_content_credentials: bool = False


def get_digital_source_type_term(digital_source_type):
    """Return the IPTC term (e.g. ``trainedAlgorithmicMedia``) of a digital source type URI."""
    return (digital_source_type or "").rstrip("/").rsplit("/", 1)[-1]


def get_digital_source_type_label(digital_source_type):
    term = get_digital_source_type_term(digital_source_type)
    return DIGITAL_SOURCE_TYPE_LABELS.get(term, term)


def is_ai_digital_source_type(digital_source_type):
    return get_digital_source_type_term(digital_source_type) in AI_DIGITAL_SOURCE_TYPES


def normalize_digital_source_type(value):
    """Return the full IPTC URI for a digital source type or an empty string if
    the value is unusable. Bare terms are expanded to the IPTC vocabulary URI."""
    value = (value or "").strip()
    if not value or len(value) > MAX_DIGITAL_SOURCE_TYPE_LENGTH:
        return ""
    if re.fullmatch(r"[A-Za-z]+", value):
        return IPTC_DIGITAL_SOURCE_TYPE_BASE + value
    if re.fullmatch(r"https?://[^\s\"'<>]+", value):
        return value.rstrip("/")
    return ""


def ai_digital_source_type_q(field="digital_source_type"):
    """Return a ``Q`` object matching images created or edited using generative AI."""
    q = Q()
    for term in AI_DIGITAL_SOURCE_TYPES:
        q |= Q(**{f"{field}__endswith": "/" + term})
    return q


def build_xmp_packet(digital_source_type):
    """Return a minimal XMP packet stating only the digital source type."""
    return (
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about="" '
        'xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/" '
        f'Iptc4xmpExt:DigitalSourceType={quoteattr(digital_source_type)}/>'
        '</rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
    ).encode()


def insert_jpeg_xmp(data, xmp):
    """Return the JPEG ``data`` with an APP1 segment holding the XMP packet
    inserted after the SOI marker and a JFIF APP0 segment, if present."""
    payload = JPEG_XMP_IDENTIFIER + xmp
    segment = b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload
    position = 2
    if data[2:4] == b"\xff\xe0":
        position += 2 + struct.unpack(">H", data[4:6])[0]
    return data[:position] + segment + data[position:]


def get_xmp_packet(pil_image):
    """Return the XMP packet Pillow found in the image as text, or ``""``."""
    info = getattr(pil_image, "info", None) or {}
    for key in XMP_INFO_KEYS:
        xmp = info.get(key)
        if xmp:
            break
    else:
        # Pillow < 11 only keeps a JPEG's XMP packet in its list of APP segments
        for marker, content in getattr(pil_image, "applist", ()):
            if marker == "APP1" and content.startswith(JPEG_XMP_IDENTIFIER):
                xmp = content[len(JPEG_XMP_IDENTIFIER):]
                break
        else:
            return ""
    if isinstance(xmp, bytes):
        xmp = xmp[:MAX_XMP_SIZE].decode("utf-8", errors="ignore")
    return str(xmp)[:MAX_XMP_SIZE]


def _png_xmp(file):
    # Pillow reads text chunks after the image data only when decoding the image
    file.seek(8)  # Skip signature
    for _i in range(MAX_BLOCKS):
        length, chunk_type = struct.unpack(">I4s", _read_exactly(file, 8))
        if chunk_type == b"IEND":
            return b""
        if chunk_type == b"iTXt" and length <= MAX_XMP_SIZE + 1024:
            data = _read_exactly(file, length)
            if data.startswith(PNG_XMP_KEYWORD):
                compressed, method = data[len(PNG_XMP_KEYWORD):len(PNG_XMP_KEYWORD) + 2]
                # Language tag and translated keyword precede the text
                text = data[len(PNG_XMP_KEYWORD) + 2:].split(b"\x00", 2)[-1]
                if compressed:
                    # Limit the output: the text is untrusted
                    text = zlib.decompressobj().decompress(text, MAX_XMP_SIZE) if method == 0 else b""
                return text
            file.seek(4, 1)  # CRC
        else:
            file.seek(length + 4, 1)  # Chunk data and CRC
    return b""


def _skip_gif_sub_blocks(file):
    while size := _read_exactly(file, 1)[0]:
        file.seek(size, 1)


def _gif_header_size(data):
    flags = data[10]  # Logical screen descriptor
    return 13 + (3 << ((flags & 7) + 1) if flags & 0x80 else 0)  # Global color table


def _find_gif_application_extension(file, match):
    """Walk the blocks of a GIF file and return the identifier of the first
    application extension for which ``match(identifier)`` is true, leaving the
    file positioned after it. Return ``None`` if there is none."""
    file.seek(0)
    file.seek(_gif_header_size(_read_exactly(file, 13)))
    for _i in range(MAX_BLOCKS):
        introducer = file.read(1)
        if introducer == b"!":  # Extension
            label = _read_exactly(file, 1)[0]
            if label == 0xFF:  # Application extension
                identifier = _read_exactly(file, _read_exactly(file, 1)[0])
                if match(identifier):
                    return identifier
            _skip_gif_sub_blocks(file)
        elif introducer == b",":  # Image descriptor
            flags = _read_exactly(file, 9)[8]
            if flags & 0x80:
                file.seek(3 << ((flags & 7) + 1), 1)  # Local color table
            file.seek(1, 1)  # LZW minimum code size
            _skip_gif_sub_blocks(file)
        else:  # Trailer or invalid data
            return None
    return None


def _gif_xmp(file):
    # Pillow does not read the XMP application extension
    if _find_gif_application_extension(file, GIF_XMP_IDENTIFIER.__eq__) is None:
        return b""
    data = file.read(MAX_XMP_SIZE)
    end = data.find(GIF_XMP_TRAILER)
    return data[:end] if end >= 0 else b""


def insert_gif_xmp(data, xmp):
    """Return the GIF ``data`` with an XMP application extension inserted
    before the first image."""
    position = _gif_header_size(data)
    extension = b"!\xff\x0b" + GIF_XMP_IDENTIFIER + xmp + GIF_XMP_MAGIC_TRAILER
    return data[:position] + extension + data[position:]


def read_xmp_packet(file):
    """Return the XMP packet of a PNG or GIF file where Pillow does not expose
    it without decoding the image, or ``b""``. The file position is restored."""
    position = file.tell()
    try:
        file.seek(0)
        head = file.read(8)
        if head == b"\x89PNG\r\n\x1a\n":
            return _png_xmp(file)
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return _gif_xmp(file)
    except (EOFError, OSError, ValueError, struct.error, zlib.error):
        # Best-effort parsing: malformed/unsupported input yields no XMP.
        pass
    finally:
        file.seek(position)
    return b""


def detect_digital_source_type(pil_image, file=None):
    """Return the IPTC digital source type URI stated in the image's XMP packet
    or an empty string. Pass the image's ``file`` to also find XMP packets that
    Pillow does not expose (PNG after the image data, GIF)."""
    xmp = get_xmp_packet(pil_image)
    if not xmp and file is not None:
        xmp = read_xmp_packet(file)[:MAX_XMP_SIZE].decode("utf-8", errors="ignore")
    if "DigitalSourceType" not in xmp:
        return ""
    for pattern in _DIGITAL_SOURCE_TYPE_PATTERNS:
        match = pattern.search(xmp)
        if match:
            return normalize_digital_source_type(match.group(2))
    return ""


def _read_exactly(file, size):
    data = file.read(size)
    if len(data) != size:
        raise EOFError
    return data


def _jpeg_has_c2pa(file):
    # C2PA manifest stores are JUMBF boxes in APP11 segments before the image data
    file.seek(2)  # Skip SOI marker
    for _i in range(MAX_BLOCKS):
        marker = _read_exactly(file, 2)
        if marker[0] != 0xFF:
            return False
        if marker[1] == 0xFF:  # Fill byte
            file.seek(-1, 1)
            continue
        if marker[1] in (0x01, *range(0xD0, 0xD8)):  # Markers without payload
            continue
        if marker[1] in (0xD9, 0xDA):  # End of image, start of scan
            return False
        length = struct.unpack(">H", _read_exactly(file, 2))[0] - 2
        if length < 0:
            return False
        if marker[1] == 0xEB:  # APP11
            payload = _read_exactly(file, length)
            # "JP" common identifier, followed by a JUMBF superbox
            if payload[:2] == b"JP" and b"jumb" in payload and C2PA_JUMBF_LABEL in payload:
                return True
        else:
            file.seek(length, 1)
    return False


def _png_has_c2pa(file):
    file.seek(8)  # Skip signature
    for _i in range(MAX_BLOCKS):
        length, chunk_type = struct.unpack(">I4s", _read_exactly(file, 8))
        if chunk_type == b"caBX":
            return True
        if chunk_type == b"IEND":
            return False
        file.seek(length + 4, 1)  # Chunk data and CRC
    return False


def _riff_has_c2pa(file):
    file.seek(12)  # Skip RIFF header and form type
    for _i in range(MAX_BLOCKS):
        fourcc, size = struct.unpack("<4sI", _read_exactly(file, 8))
        if fourcc == b"C2PA":
            return True
        file.seek(size + (size & 1), 1)  # Chunks are padded to an even size
    return False


def _isobmff_has_c2pa(file):
    # AVIF, HEIF: the manifest store is a top-level ``uuid`` box with the C2PA UUID
    file.seek(0)
    for _i in range(MAX_BLOCKS):
        header = file.read(8)
        if len(header) < 8:
            return False
        size, box_type = struct.unpack(">I4s", header)
        header_size = 8
        if size == 1:
            size = struct.unpack(">Q", _read_exactly(file, 8))[0]
            header_size = 16
        if box_type == b"uuid" and _read_exactly(file, 16) == C2PA_ISOBMFF_UUID:
            return True
        if size == 0:  # Box extends to the end of the file
            return False
        if size < header_size:
            return False
        file.seek(size - header_size - (16 if box_type == b"uuid" else 0), 1)
    return False


def _gif_has_c2pa(file):
    # An application extension "C2PA_GIF" with the manifest store in its sub-blocks
    return _find_gif_application_extension(file, lambda identifier: identifier[:8] == C2PA_GIF_IDENTIFIER) is not None


def detect_content_credentials(file):
    """Return ``True`` if the file embeds a C2PA manifest store. The manifest
    is not validated. Supports JPEG, PNG, GIF, WebP and ISO base media files
    (AVIF, HEIF). The file position is not restored."""
    try:
        file.seek(0)
        head = file.read(12)
        if head[:2] == b"\xff\xd8":
            return _jpeg_has_c2pa(file)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return _png_has_c2pa(file)
        if head[:4] == b"RIFF":
            return _riff_has_c2pa(file)
        if head[4:8] == b"ftyp":
            return _isobmff_has_c2pa(file)
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return _gif_has_c2pa(file)
    except (EOFError, OSError, ValueError, struct.error):
        # Best effort: malformed or unreadable files are treated as having no
        # detectable content credentials.
        return False
    return False


def detect_provenance(file, pil_image):
    """Detect provenance information of an image. ``file`` is the raw file
    object, ``pil_image`` the image opened from it by Pillow."""
    return Provenance(
        digital_source_type=detect_digital_source_type(pil_image, file),
        has_content_credentials=detect_content_credentials(file),
    )


def detect_file_provenance(file):
    """Detect provenance information of an image file object. The file
    position is reset to its start."""
    from PIL import Image

    try:
        file.seek(0)
        return detect_provenance(file, Image.open(file))
    except Exception:
        return Provenance()
    finally:
        try:
            file.seek(0)
        except Exception:
            pass
