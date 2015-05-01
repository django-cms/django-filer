# -*- coding: utf-8 -*-
from distutils.version import LooseVersion
import sys

import django
from django.utils import six

try:
    from django.utils.text import truncate_words
except ImportError:
    # django >=1.5
    from django.utils.text import Truncator
    from django.utils.functional import allow_lazy
    def truncate_words(s, num, end_text='...'):
        truncate = end_text and ' %s' % end_text or ''
        return Truncator(s).words(num, truncate=truncate)
    truncate_words = allow_lazy(truncate_words, six.text_type)

DJANGO_1_4 = LooseVersion(django.get_version()) < LooseVersion('1.5')
DJANGO_1_5 = LooseVersion(django.get_version()) < LooseVersion('1.6')
DJANGO_1_6 = LooseVersion(django.get_version()) < LooseVersion('1.7')
DJANGO_1_7 = LooseVersion(django.get_version()) < LooseVersion('1.8')
DJANGO_1_8 = LooseVersion(django.get_version()) < LooseVersion('1.9')


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
    from django.utils.encoding import force_unicode
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
    from django.utils.encoding import python_2_unicode_compatible


def get_delete_permission(opts):
    try:
        from django.contrib.auth import get_permission_codename
        return '%s.%s' % (opts.app_label,
                          get_permission_codename('delete', opts))
    except ImportError:
        return '%s.%s' % (opts.app_label,
                          opts.get_delete_permission())
