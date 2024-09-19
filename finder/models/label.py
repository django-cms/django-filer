from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _, ngettext


class Label(models.Model):
    name = models.CharField(
        _("Name"),
        max_length=255,
        unique=True,
    )
    color = models.CharField(
        _("Color"),
        max_length=7,
        default='#000000',
    )

    class Meta:
        verbose_name = _("Label")
        verbose_name_plural = _("Labels")

    def __str__(self):
        return self.name
