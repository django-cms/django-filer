#-*- coding: utf-8 -*-
from django.template import Library

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
