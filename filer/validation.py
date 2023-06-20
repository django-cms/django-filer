from django.utils.translation import gettext as _


class FileValidationError(Exception):
    pass


def deny_html(file_name, file, owner, mime_type):
    """Simple validator that denies all files"""
    raise FileValidationError(
        _('File "{}": HTML upload denied by site security policy').format(file_name))


def validate_svg(file_name, file, owner, mime_type):
    """SVG files must not contain script tags or javascript hrefs.
    This might be too strict but avoids parsing the xml"""
    content = file.read()
    if b"<script" in content or b"javascript:" in content:
        raise FileValidationError(
            _('File "{}": Rejected due to potential cross site scripting attack').format(file_name)
        )


DEFAULT_VALIDATORS = [
    ("text/html", deny_html),
    ("image/svg+xml", validate_svg),
]


def validate_upload(file_name, file, owner, mime_type) -> None:
    for mt, validator in DEFAULT_VALIDATORS:
        if mime_type == mt:
            validator(file_name, file, owner, mime_type)
