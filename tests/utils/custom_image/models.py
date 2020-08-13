from django.db import models

from filer.models.abstract import BaseImage


class Image(BaseImage):
    extra_description = models.TextField()

    class Meta(BaseImage.Meta):
        swappable = 'FILER_IMAGE_MODEL'
        app_label = 'custom_image'
        default_manager_name = 'objects'
