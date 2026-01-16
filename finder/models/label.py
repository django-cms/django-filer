from django.db import models
from django.utils.translation import gettext_lazy as _

from finder.models.ambit import AmbitModel


class Label(models.Model):
    ambit = models.ForeignKey(
        AmbitModel,
        on_delete=models.CASCADE,
        related_name='labels',
        editable=False,
    )
    name = models.CharField(
        _("Name"),
        max_length=255,
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
