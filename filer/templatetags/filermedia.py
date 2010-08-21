from django.template import Library
import math
import re

SIZE_RE = re.compile('\d+x\d+')

register = Library()

def filer_staticmedia_prefix():
    """
    Returns the string contained in the setting FILER_STATICMEDIA_PREFIX.
    """
    try:
        from filer import settings
    except ImportError:
        return ''
    return settings.FILER_STATICMEDIA_PREFIX
filer_staticmedia_prefix = register.simple_tag(filer_staticmedia_prefix)


def _recalculate_size(size, index, divisor=0, padding=0):
    new_one = size[index]
    if divisor:
        new_one = new_one / float(divisor)
    if padding:
        new_one = new_one - padding
    new_two = int(float(new_one)*float(size[int(not index)])/size[index])
    new_one = int(new_one)
    if index:
        return (new_two, new_one)
    return new_one, new_two


def _resize(original_size, index, divisor=0, padding=0):
    if not SIZE_RE.match(original_size):
        return original_size
    else:
        original_size = [int(part) for part in original_size.split('x')]
    try:
        padding = int(padding)
        divisor = int(divisor)
    except (TypeError, ValueError):
        return original_size
    # Re-calculate size
    new_x, new_y = _recalculate_size(original_size, index, divisor=divisor, padding=padding)
    return '%sx%s' % (new_x, new_y)

def extra_padding_x(original_size, padding):
    """
    Reduce the width of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _resize(original_size, 0, padding=padding)
extra_padding_x = register.filter(extra_padding_x)

def extra_padding_y(original_size, padding):
    """
    Reduce the height of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _resize(original_size, 1, padding=padding)
extra_padding_y = register.filter(extra_padding_y)

def devide_x_by(original_size, divisor):
    """
    Reduce by half
    """
    return _resize(original_size, 0, divisor=divisor)
devide_x_by = register.filter(devide_x_by)

def devide_y_by(original_size, divisor):
    """
    Reduce by half
    """
    return _resize(original_size, 1, divisor=divisor)
devide_y_by = register.filter(devide_y_by)

# The templatetag below is copied from sorl.thumbnail

filesize_formats = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
filesize_long_formats = {
    'k': 'kilo', 'M': 'mega', 'G': 'giga', 'T': 'tera', 'P': 'peta',
    'E': 'exa', 'Z': 'zetta', 'Y': 'yotta',
}



def filesize(bytes, format='auto1024'):
    """
    Returns the number of bytes in either the nearest unit or a specific unit
    (depending on the chosen format method).

    Acceptable formats are:

    auto1024, auto1000
      convert to the nearest unit, appending the abbreviated unit name to the
      string (e.g. '2 KiB' or '2 kB').
      auto1024 is the default format.
    auto1024long, auto1000long
      convert to the nearest multiple of 1024 or 1000, appending the correctly
      pluralized unit name to the string (e.g. '2 kibibytes' or '2 kilobytes').
    kB, MB, GB, TB, PB, EB, ZB or YB
      convert to the exact unit (using multiples of 1000).
    KiB, MiB, GiB, TiB, PiB, EiB, ZiB or YiB
      convert to the exact unit (using multiples of 1024).

    The auto1024 and auto1000 formats return a string, appending the correct
    unit to the value. All other formats return the floating point value.

    If an invalid format is specified, the bytes are returned unchanged.
    """
    format_len = len(format)
    # Check for valid format
    if format_len in (2, 3):
        if format_len == 3 and format[0] == 'K':
            format = 'k%s' % format[1:]
        if not format[-1] == 'B' or format[0] not in filesize_formats:
            return bytes
        if format_len == 3 and format[1] != 'i':
            return bytes
    elif format not in ('auto1024', 'auto1000',
                        'auto1024long', 'auto1000long'):
        return bytes
    # Check for valid bytes
    try:
        bytes = long(bytes)
    except (ValueError, TypeError):
        return bytes

    # Auto multiple of 1000 or 1024
    if format.startswith('auto'):
        if format[4:8] == '1000':
            base = 1000
        else:
            base = 1024
        logarithm = bytes and math.log(bytes, base) or 0
        index = min(int(logarithm) - 1, len(filesize_formats) - 1)
        if index >= 0:
            if base == 1000:
                bytes = bytes and bytes / math.pow(1000, index + 1)
            else:
                bytes = bytes >> (10 * (index))
                bytes = bytes and bytes / 1024.0
            unit = filesize_formats[index]
        else:
            # Change the base to 1000 so the unit will just output 'B' not 'iB'
            base = 1000
            unit = ''
        if bytes >= 10 or ('%.1f' % bytes).endswith('.0'):
            bytes = '%.0f' % bytes
        else:
            bytes = '%.1f' % bytes
        if format.endswith('long'):
            unit = filesize_long_formats.get(unit, '')
            if base == 1024 and unit:
                unit = '%sbi' % unit[:2]
            unit = '%sbyte%s' % (unit, bytes != '1' and 's' or '')
        else:
            unit = '%s%s' % (base == 1024 and unit.upper() or unit,
                             base == 1024 and 'iB' or 'B')

        return '%s %s' % (bytes, unit)

    if bytes == 0:
        return bytes
    base = filesize_formats.index(format[0]) + 1
    # Exact multiple of 1000
    if format_len == 2:
        return bytes / (1000.0 ** base)
    # Exact multiple of 1024
    elif format_len == 3:
        bytes = bytes >> (10 * (base - 1))
        return bytes / 1024.0


register.filter(filesize)
