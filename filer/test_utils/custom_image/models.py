# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.db import models

from ...models.abstract import BaseImage


class Image(BaseImage):
    extra_description = models.TextField()

    class Meta(object):
        app_label = 'custom_image'
