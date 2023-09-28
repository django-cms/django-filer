import typing

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


User = get_user_model()  # Needed for typing


class FileValidationError(ValidationError):
    pass


def deny(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    file_type = file_name.rsplit(".")[-1]
    if file_type == file_name:
        raise FileValidationError(
            _('File "{file_name}": Upload denied by site security policy').format(file_name=file_name)
        )
    raise FileValidationError(
        _('File "{file_name}": {file_type} upload denied by site security policy').format(
            file_name=file_name,
            file_type=file_type.upper()
        )
    )


def deny_html(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    """Simple validator that denies all files. Separate for HTML since .html and .htm are both
    common suffixes for text/html files."""
    raise FileValidationError(
        _('File "{file_name}": HTML upload denied by site security policy').format(file_name=file_name)
    )


TRIGGER_XSS_THREAD = (
    # Part 1: Event attributes that take js code as values
    # See https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/Events
    b"onbegin=", b"onend=", b"onrepeat=",
    b"onabort=", b"onerror=", b"onresize=", b"onscroll=", b"onunload=",
    b"oncopy=", b"oncut=", b"onpaste=",
    b"oncancel=", b"oncanplay=", b"oncanplaythrough=", b"onchange=", b"onclick=", b"onclose=", b"oncuechange=", b"ondblclick=",
    b"ondrag=", b"ondragend=", b"ondragenter=", b"ondragleave=", b"ondragover=", b"ondragstart=", b"ondrop=",
    b"ondurationchange=", b"onemptied=", b"onended=", b"onerror=", b"onfocus=", b"oninput=", b"oninvalid=",
    b"onkeydown=", b"onkeypress=", b"onkeyup=", b"onload=", b"onloadeddata=", b"onloadedmetadata=", b"onloadstart=",
    b"onmousedown=", b"onmouseenter=", b"onmouseleave=", b"onmousemove=", b"onmouseout=", b"onmouseover=", b"onmouseup=",
    b"onmousewheel=", b"onpause=", b"onplay=", b"onplaying=", b"onprogress=", b"onratechange=", b"onreset=", b"onresize=",
    b"onscroll=", b"onseeked=", b"onseeking=", b"onselect=", b"onshow=", b"onstalled=", b"onsubmit=", b"onsuspend=",
    b"ontimeupdate=", b"ontoggle==", b"onvolumechange==", b"onwaiting=",
    b"onactivate=", b"onfocusin=", b"onfocusout=",
) + (
    # Part 2:
    # Reject base64 obfuscated content
    b";base64,",
) + (
    # Part 3: Obvious scripts
    # Reject direct <scrpit> tags or javascript: uri
    b"<script",
    b"javascript:",
)


def validate_svg(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    """SVG files must not contain script tags or javascript hrefs.
    This might be too strict but avoids parsing the xml"""
    content = file.read().lower()
    if any(map(lambda x: x in content, TRIGGER_XSS_THREAD)):
        # If any element of TRIGGER_XSS_THREAD is found in file, raise FileValidationError
        raise FileValidationError(
            _('File "{file_name}": Rejected due to potential cross site scripting vulnerability')
            .format(file_name=file_name)
        )


def sanitize_svg(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    from easy_thumbnails.VIL.Image import Image
    from reportlab.graphics import renderSVG
    from svglib.svglib import svg2rlg
    drawing = svg2rlg(file)
    if not drawing:
        raise FileValidationError(
            _('File "{file_name}": SVG file format not recognized')
            .format(file_name=file_name)
        )
    image = Image(size=(drawing.width, drawing.height))
    renderSVG.draw(drawing, image.canvas)
    xml = image.canvas.svg.toxml(encoding="UTF-8")  # Removes non-graphic nodes ->  sanitation
    file.seek(0)  # Rewind file
    file.write(xml)  # write to binary file with utf-8 encoding


def validate_upload(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    """Actual validation: Call all validators for the given mime type. The app config reads
    the validators from the settings and replaces dotted paths by callables."""

    config = apps.get_app_config("filer")

    # First, check white list if provided
    if config.MIME_TYPE_WHITELIST:
        # FILER_MIME_TYPE_WHITELIST restricts the allowed mime types to, e.g., "image/*" or "text/plain"
        for allowed_mime_type in config.MIME_TYPE_WHITELIST:
            if mime_type == allowed_mime_type:
                break
            elif "/" in allowed_mime_type and [mime_type.split("/")[0], "*"] == allowed_mime_type.split("/", 1):
                break
        else:
            # No match found <=> no break in for loop? Deny file
            deny(file_name, file, owner, mime_type)

    # Second, check upload validators
    if mime_type in config.FILE_VALIDATORS:
        for validator in config.FILE_VALIDATORS[mime_type]:
            validator(file_name, file, owner, mime_type)
