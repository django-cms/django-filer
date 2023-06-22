import typing

from django.apps import apps
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _


User = get_user_model()


class FileValidationError(Exception):
    pass


def deny_html(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    """Simple validator that denies all files"""
    raise FileValidationError(
        _('File "{}": HTML upload denied by site security policy').format(file_name)
    )


def deny(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    file_type = file_name.rsplit(".")[-1]
    if file_type == file_name:
        raise FileValidationError(
            _('File "{}": Upload denied by site security policy').format(file_name)
        )
    raise FileValidationError(
        _('File "{}": {} upload denied by site security policy').format(file_name, file_type.upper())
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
            _('File "{}": Rejected due to potential cross site scripting vulnerability').format(file_name)
        )


def validate_upload(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    """Actual validation: Call all validators for the given mime type. The app config reads
    the validators from the settings and replaces dotted paths by callables."""

    config = apps.get_app_config("filer")

    if mime_type in config.FILE_VALIDATORS:
        for validator in config.FILE_VALIDATORS[mime_type]:
            validator(file_name, file, owner, mime_type)
