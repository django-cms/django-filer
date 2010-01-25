from os.path import join
from django.conf import settings

FILER_STATICMEDIA_PREFIX = getattr(settings, 'FILER_STATICMEDIA_PREFIX', join(settings.MEDIA_URL,'filer/') )

FILER_UPLOAD_ROOT = getattr(settings,'FILER_UPLOAD_ROOT', 'catalogue')

FILER_ADMIN_ICON_SIZES = (
        '32','48','64',
)