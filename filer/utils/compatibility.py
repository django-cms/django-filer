# -*- coding: utf-8 -*-
from distutils.version import LooseVersion
import django

try:
    from django.utils.text import truncate_words
except ImportError:
    # django >=1.5
    from django.utils.text import Truncator
    from django.utils.functional import allow_lazy
    def truncate_words(s, num, end_text='...'):
        truncate = end_text and ' %s' % end_text or ''
        return Truncator(s).words(num, truncate=truncate)
    truncate_words = allow_lazy(truncate_words, unicode)

DJANGO_1_4 = LooseVersion(django.get_version()) < LooseVersion('1.5')
