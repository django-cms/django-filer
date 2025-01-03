from django.db import models

from finder.models.fields import FinderFileField


class DemoAppModel(models.Model):
    file = FinderFileField(
        verbose_name="Demo File",
        null=True,
        blank=True,
    )
