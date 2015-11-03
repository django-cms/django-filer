# -*- coding: utf-8 -*-
from django.db import models

from filer.models.abstract import BaseImage


class Image(BaseImage):
    extra_description = models.TextField()

    class Meta:
        app_label = 'custom_image'
