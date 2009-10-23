from django.conf import settings as globalsettings
from filer import settings

def media(request):
    """
    Adds media-related context variables to the context.
    """
    return {'FILER_MEDIA_URL': settings.FILER_MEDIA_URL,
            # This would better be exported by django's context_processor.media.
            'ADMIN_MEDIA_PREFIX': globalsettings.ADMIN_MEDIA_PREFIX}
