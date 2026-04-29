from django.db import models

from finder.models.fields import FinderFileField, FinderFolderField


class DemoAppModel(models.Model):
    file = FinderFileField(
        models.SET_DEFAULT,
        verbose_name="Demo File",
        null=True,
        blank=True,
        accept_mime_types=['image/*'],
        ambit='public',
    )
    folder = FinderFolderField(
        on_delete=models.SET_DEFAULT,
        verbose_name="Demo Folder",
        null=True,
        blank=True,
        ambit='public',
    )
