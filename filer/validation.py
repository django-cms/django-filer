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
    "onbegin=", "onend=", "onrepeat=",
    "onabort=", "onerror=", "onresize=", "onscroll=", "onunload=",
    "oncopy=", "oncut=", "onpaste=",
    "oncancel=", "oncanplay=", "oncanplaythrough=", "onchange=", "onclick=", "onclose=", "oncuechange=", "ondblclick=",
    "ondrag=", "ondragend=", "ondragenter=", "ondragleave=", "ondragover=", "ondragstart=", "ondrop=",
    "ondurationchange=", "onemptied=", "onended=", "onerror=", "onfocus=", "oninput=", "oninvalid=",
    "onkeydown=", "onkeypress=", "onkeyup=", "onload=", "onloadeddata=", "onloadedmetadata=", "onloadstart=",
    "onmousedown=", "onmouseenter=", "onmouseleave=", "onmousemove=", "onmouseout=", "onmouseover=", "onmouseup=",
    "onmousewheel=", "onpause=", "onplay=", "onplaying=", "onprogress=", "onratechange=", "onreset=", "onresize=",
    "onscroll=", "onseeked=", "onseeking=", "onselect=", "onshow=", "onstalled=", "onsubmit=", "onsuspend=",
    "ontimeupdate=", "ontoggle=", "onvolumechange=", "onwaiting=",
    "onactivate=", "onfocusin=", "onfocusout=",
) + (
    # Part 2:
    # Reject base64 obfuscated content
    ";base64,",
) + (
    # Part 3: Obvious scripts
    # Reject direct <scrpit> tags or javascript: uri
    "<script",
    "javascript:",
)


def validate_svg(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    """SVG files must not contain script tags or javascript hrefs.
    This might be too strict but avoids parsing the xml"""

    from html import unescape

    content = unescape(file.read().decode('utf-8').lower())
    if any(map(lambda x: x in content, TRIGGER_XSS_THREAD)):
        import warnings

        warnings.warn(
            "SVG validation via string matching is deprecated and will be removed. "
            "SVGs will be sanitized instead. Remove this message by removing "
            "{\"image/svg+xml\": [\"filer.validation.sanitize_svg\"]} from your "
            "FILER_ADD_FILE_VALIDATORS settings",
            DeprecationWarning,
            stacklevel=2,
        )
        # If any element of TRIGGER_XSS_THREAD is found in file, raise FileValidationError
        raise FileValidationError(
            _('File "{file_name}": Rejected due to potential cross site scripting vulnerability')
            .format(file_name=file_name)
        )


def sanitize_svg(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    from py_svg_hush import filter_svg

    content = file.read()
    try:
        sanitized = filter_svg(content)
    except Exception:
        sanitized = None

    if sanitized is None:
        raise FileValidationError(
            _('File "{file_name}": Rejected due to incompatible format')
            .format(file_name=file_name)
        )

    file.seek(0)  # Rewind file
    file.truncate()  # Delete old content
    file.write(sanitized)  # write to binary file with utf-8 encoding


def validate_upload(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
    """Actual validation: Call all validators for the given MIME type. The app config reads
    the validators from the settings and replaces dotted paths by callables."""

    config = apps.get_app_config("filer")

    # First, check white list if provided
    if config.MIME_TYPE_WHITELIST:
        # FILER_MIME_TYPE_WHITELIST restricts the allowed MIME types to, e.g., "image/*" or "text/plain"
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
