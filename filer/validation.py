from django.apps import apps
from django.utils.translation import gettext as _


class FileValidationError(Exception):
    pass


def deny_html(file_name, file, owner, mime_type):
    """Simple validator that denies all files"""
    raise FileValidationError(
        _('File "{}": HTML upload denied by site security policy').format(file_name)
    )


def validate_svg(file_name, file, owner, mime_type):
    """SVG files must not contain script tags or javascript hrefs.
    This might be too strict but avoids parsing the xml"""
    content = file.read()
    if b"<script" in content or b"javascript:" in content:
        raise FileValidationError(
            _('File "{}": Rejected due to potential cross site scripting attack').format(file_name)
        )


def validate_upload(file_name, file, owner, mime_type) -> None:
    config = apps.get_app_config("filer")

    for mt, validators in config.FILE_VALIDATORS.items():
        if mime_type == mt:
            for validator in validators:
                validator(file_name, file, owner, mime_type)
