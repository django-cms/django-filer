from django.conf import settings

def media(request):
    """
    Adds media-related context variables to the context.
    """
    # Use special variable from projects settings or fall back to the
    # general media URL.
    try:
        result = settings.IMAGE_FILER_MEDIA_URL
    except AttributeError:
        try:
            result = settings.MEDIA_URL+'filer/'
        except:
            result = ""
    
    return {'FILER_MEDIA_URL': result,
            # This would better be exported by django's context_processor.media.
            'ADMIN_MEDIA_PREFIX': settings.ADMIN_MEDIA_PREFIX}
