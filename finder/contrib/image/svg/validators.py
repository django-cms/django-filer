from django.utils.translation import gettext_lazy as _

from finder.exceptions import FileValidationError


def sanitize_svg(file_name, file_handle, owner, mime_type):
    """
    Rewrite an uploaded SVG with everything a browser would execute removed.

    This is a sanitizing validator: it does not reject a document carrying scripts, it
    stores the document without them. It is registered for 'image/svg+xml' by default,
    because an SVG is served from the media origin and is executed by the browser without
    any warning.
    """
    try:
        from py_svg_hush import filter_svg
    except ImportError:
        # Fail closed: without a sanitizer there is no safe way to accept the document.
        raise FileValidationError(
            _('File “{file_name}”: SVG uploads are rejected because py-svg-hush is not '
              'installed. Install django-finder[svg] to enable them, or drop the validator '
              'through FINDER_REMOVE_PAYLOAD_VALIDATORS.')
            .format(file_name=file_name)
        )

    try:
        sanitized = filter_svg(file_handle.read())
    except ValueError as exc:
        raise FileValidationError(
            _('File “{file_name}”: Invalid or malicious SVG ({reason}).')
            .format(file_name=file_name, reason=exc)
        )
    if sanitized is None:
        raise FileValidationError(
            _('File “{file_name}”: Rejected due to incompatible format.')
            .format(file_name=file_name)
        )

    file_handle.seek(0)
    file_handle.truncate()
    file_handle.write(sanitized)


def svg_validator(file_name, file_handle, owner, mime_type):
    """
    check for malicious tags not part of the SVG standard
    """
    try:
        from py_svg_hush import filter_svg
    except ImportError:
        return

    try:
        filter_svg(file_handle.read())
    except ValueError as exc:
        raise ValueError(f"Invalid or malicious SVG in “{file_name}”: {exc}")


def xml_validator(file_name, file_handle, owner, mime_type):
    """
    check against XXE, billion laughs, etc.
    """
    try:
        import defusedxml.ElementTree as ET
    except ImportError:
        return

    try:
        ET.fromstring(file_handle.read())
    except ET.ParseError as exc:
        raise ValueError(f"Invalid or malicious SVG in “{file_name}”: {exc}")
