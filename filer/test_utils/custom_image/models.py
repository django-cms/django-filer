# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.db import models

from ...models.abstract import BaseImage
from ...utils.compatibility import GTE_DJANGO_1_10


class Image(BaseImage):
    extra_description = models.TextField()

    class Meta(BaseImage.Meta):
        swappable = 'FILER_IMAGE_MODEL'
        app_label = 'custom_image'
        if GTE_DJANGO_1_10:
            default_manager_name = 'objects'
