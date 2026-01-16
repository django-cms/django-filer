from django.db import models

from finder.models.fields import FinderFileField, FinderFolderField


class DemoAppModel(models.Model):
    file = FinderFileField(
        verbose_name="Demo File",
        null=True,
        blank=True,
        accept_mime_types=['image/*'],
        ambit='public',
    )
    folder = FinderFolderField(
        verbose_name="Demo Folder",
        null=True,
        blank=True,
        ambit='public',
    )
