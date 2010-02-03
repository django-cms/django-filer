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


def _recalculate_size(size, padding, index):
    new_one = size[index] - padding
    new_two = int(float(new_one)*float(size[int(not index)])/size[index])
    if index:
        return (new_two, new_one)
    return new_one, new_two

def _extra_padding(original_size, padding, index):
    if not SIZE_RE.match(original_size):
        return original_size
    else:
        original_size = [int(part) for part in original_size.split('x')]
    try:
        padding = int(padding)
    except (TypeError, ValueError):
        return original_size
    # Re-calculate size
    new_x, new_y = _recalculate_size(original_size, padding, index)
    return '%sx%s' % (new_x, new_y)


def extra_padding_x(original_size, padding):
    """
    Reduce the width of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _extra_padding(original_size, padding, 0)
extra_padding_x = register.filter(extra_padding_x)

def extra_padding_y(original_size, padding):
    """
    Reduce the height of `original_size` by `padding`, maintaining the aspect
    ratio.
    """
    return _extra_padding(original_size, padding, 1)
extra_padding_y = register.filter(extra_padding_y)