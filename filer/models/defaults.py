from django.conf import settings

IMAGE_FILER_UPLOAD_ROOT = getattr(settings,'IMAGE_FILER_UPLOAD_ROOT', 'catalogue')

DEFAULT_ICON_SIZES = (
        '32','48','64',
)