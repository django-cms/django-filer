from os.path import join
from django.conf import settings

FILER_MEDIA_URL = getattr(settings, 'FILER_MEDIA_URL', join(settings.MEDIA_URL,'filer/') )