from django.apps import apps
from django.utils.translation import gettext as _


class FileValidationError(Exception):
    pass


def deny_html(file_name, file, owner, mime_type):
    """Simple validator that denies all files"""
    raise FileValidationError(
        _('File "{}": HTML upload denied by site security policy').format(file_name)
    )


EVENT_ATTRIBUTES = (
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
    # Reject base64 obfuscated content
    b";base64,",
)


def validate_svg(file_name, file, owner, mime_type):
    """SVG files must not contain script tags or javascript hrefs.
    This might be too strict but avoids parsing the xml"""
    content = file.read().lower()
    if any(map(lambda x: x in content, EVENT_ATTRIBUTES)) or b"<script" in content or b"javascript:" in content:
        raise FileValidationError(
            _('File "{}": Rejected due to potential cross site scripting vulnerability').format(file_name)
        )


def validate_upload(file_name, file, owner, mime_type) -> None:
    config = apps.get_app_config("filer")

    for mt, validators in config.FILE_VALIDATORS.items():
        if mime_type == mt:
            for validator in validators:
                validator(file_name, file, owner, mime_type)
