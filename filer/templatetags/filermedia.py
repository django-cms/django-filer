from django.template import Library

register = Library()

def filer_media_prefix():
    """
    Returns the string contained in the setting ADMIN_MEDIA_PREFIX.
    """
    try:
        from filer import settings
    except ImportError:
        return ''
    return settings.FILER_MEDIA_PREFIX
admin_media_prefix = register.simple_tag(filer_media_prefix)
