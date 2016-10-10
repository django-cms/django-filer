# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils.timezone import get_current_timezone, make_aware, now
from django.utils.translation import ugettext_lazy as _

from .. import settings as filer_settings
from ..utils.compatibility import GTE_DJANGO_1_10
from ..utils.loader import load_object
from .abstract import BaseImage

logger = logging.getLogger("filer")


if not filer_settings.FILER_IMAGE_MODEL:
    # This is the standard Image model
    class Image(BaseImage):
        date_taken = models.DateTimeField(_('date taken'), null=True, blank=True,
                                          editable=False)
        author = models.CharField(_('author'), max_length=255, null=True, blank=True)
        must_always_publish_author_credit = models.BooleanField(_('must always publish author credit'), default=False)
        must_always_publish_copyright = models.BooleanField(_('must always publish copyright'), default=False)

        class Meta(object):
            app_label = 'filer'
            verbose_name = _('image')
            verbose_name_plural = _('images')
            if GTE_DJANGO_1_10:
                default_manager_name = 'objects'

        def save(self, *args, **kwargs):
            if self.date_taken is None:
                try:
                    exif_date = self.exif.get('DateTimeOriginal', None)
                    if exif_date is not None:
                        d, t = exif_date.split(" ")
                        year, month, day = d.split(':')
                        hour, minute, second = t.split(':')
                        if getattr(settings, "USE_TZ", False):
                            tz = get_current_timezone()
                            self.date_taken = make_aware(datetime(
                                int(year), int(month), int(day),
                                int(hour), int(minute), int(second)), tz)
                        else:
                            self.date_taken = datetime(
                                int(year), int(month), int(day),
                                int(hour), int(minute), int(second))
                except Exception:
                    pass
            if self.date_taken is None:
                self.date_taken = now()
            super(Image, self).save(*args, **kwargs)

else:
    # This is just an alias for the real model defined elsewhere
    # to let imports works transparently
    Image = load_object(filer_settings.FILER_IMAGE_MODEL)
