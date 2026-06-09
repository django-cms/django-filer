from django.db import models

from finder.models.fields import FinderFileField, FinderFolderField


class SampleAppModel1(models.Model):
    file = FinderFileField(
        models.PROTECT,
        null=True,
        blank=True,
        ambit='public',
    )


class SampleAppModel2(models.Model):
    file = FinderFileField(
        models.SET_DEFAULT,
        null=True,
        blank=True,
        ambit='public',
    )


class SampleAppModel3(models.Model):
    file = FinderFileField(
        models.CASCADE,
        null=True,
        blank=True,
        accept_mime_types=['image/*'],
        ambit='public',
    )


class SampleAppModel4(models.Model):
    folder = FinderFolderField(
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        ambit='public',
    )


class SampleAppModel5(models.Model):
    folder = FinderFolderField(
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True,
        ambit='public',
    )


class SampleAppModel6(models.Model):
    folder = FinderFolderField(
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        ambit='public',
    )
