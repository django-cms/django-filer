from django.template import Library
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