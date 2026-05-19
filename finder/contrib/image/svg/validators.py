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
