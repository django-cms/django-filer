# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import sys

from django.utils.functional import keep_lazy
from django.utils.text import Truncator, format_lazy

import six


def string_concat(*strings):
    return format_lazy('{}' * len(strings), *strings)


def truncate_words(s, num, end_text='...'):
    # truncate_words was removed in Django 1.5.
    truncate = end_text and ' %s' % end_text or ''
    return Truncator(s).words(num, truncate=truncate)


truncate_words = keep_lazy(truncate_words, six.text_type)


if not six.PY3:
    fs_encoding = sys.getfilesystemencoding() or sys.getdefaultencoding()


# copied from django.utils._os (not present in Django 1.4)
def upath(path):
    """
    Always return a unicode path.
    """
    if six.PY2 and not isinstance(path, six.text_type):
        return path.decode(fs_encoding)
    return path


def get_delete_permission(opts):
    from django.contrib.auth import get_permission_codename  # noqa
    return '%s.%s' % (opts.app_label, get_permission_codename('delete', opts))


try:
    from PIL import Image as PILImage  # noqa
    from PIL import ImageDraw as PILImageDraw  # noqa
    from PIL import ExifTags as PILExifTags  # noqa
except ImportError:
    try:
        import Image as PILImage  # noqa
        import ImageDraw as PILImageDraw  # noqa
        import ExifTags as PILExifTags  # noqa
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
