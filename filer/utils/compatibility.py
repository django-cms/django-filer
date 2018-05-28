# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import sys

import django
from django.utils import six
from django.utils.functional import allow_lazy
from django.utils.text import Truncator


def truncate_words(s, num, end_text='...'):
    # truncate_words was removed in Django 1.5.
    truncate = end_text and ' %s' % end_text or ''
    return Truncator(s).words(num, truncate=truncate)
truncate_words = allow_lazy(truncate_words, six.text_type)


LTE_DJANGO_1_8 = django.VERSION < (1, 9)
LTE_DJANGO_1_9 = django.VERSION < (1, 10)
GTE_DJANGO_1_10 = django.VERSION >= (1, 10)
DJANGO_1_10 = django.VERSION[:2] == (1, 10)


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


# copied from django-cms (for compatibility with Django 1.4)
try:
    from django.utils.encoding import force_unicode  # flake8: noqa
    def python_2_unicode_compatible(klass):
        """
        A decorator that defines __unicode__ and __str__ methods under Python 2.
        Under Python 3 it does nothing.

        To support Python 2 and 3 with a single code base, define a __str__ method
        returning text and apply this decorator to the class.
        """
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
        return klass
except ImportError:
    force_unicode = lambda s: str(s)
    from django.utils.encoding import python_2_unicode_compatible  # flake8: noqa


def get_delete_permission(opts):
    try:
        from django.contrib.auth import get_permission_codename  # flake8: noqa
        return '%s.%s' % (opts.app_label,
                          get_permission_codename('delete', opts))
    except ImportError:
        return '%s.%s' % (opts.app_label,
                          opts.get_delete_permission())

try:
    from django.contrib.admin.utils import unquote, quote, NestedObjects, capfirst  # flake8: noqa
except ImportError:
    # django < 1.7
    from django.contrib.admin.util import unquote, quote, NestedObjects, capfirst  # flake8: noqa

try:
    from importlib import import_module  # flake8: noqa
except ImportError:
    # python < 2.7
    from django.utils.importlib import import_module  # flake8: noqa


try:
    from PIL import Image as PILImage
    from PIL import ImageDraw as PILImageDraw
    from PIL import ExifTags as PILExifTags
except ImportError:
    try:
        import Image as PILImage
        import ImageDraw as PILImageDraw
        import ExifTags as PILExifTags
    except ImportError:
        raise ImportError("The Python Imaging Library was not found.")
