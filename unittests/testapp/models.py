from django.db import models

from finder.models.fields import FinderFileField, FinderFolderField


class TestAppModel1(models.Model):
    file = FinderFileField(
        models.PROTECT,
        null=True,
        blank=True,
        ambit='public',
    )


class TestAppModel2(models.Model):
    file = FinderFileField(
        models.SET_DEFAULT,
        null=True,
        blank=True,
        ambit='public',
    )


class TestAppModel3(models.Model):
    file = FinderFileField(
        models.CASCADE,
        null=True,
        blank=True,
        accept_mime_types=['image/*'],
        ambit='public',
    )


class TestAppModel4(models.Model):
    folder = FinderFolderField(
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        ambit='public',
    )


class TestAppModel5(models.Model):
    folder = FinderFolderField(
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True,
        ambit='public',
    )


class TestAppModel6(models.Model):
    folder = FinderFolderField(
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        ambit='public',
    )
