import uuid

from django.db import models

from finder.models.fields import FinderFileField, FinderFolderField


# the file a `SampleAppModel9.file` falls back to once the referenced file is deleted
REPLACEMENT_FILE_ID = uuid.UUID('00000000-0000-0000-0000-0000000000ff')


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


class SampleAppModel7(models.Model):
    file = FinderFileField(
        models.SET_NULL,
        null=True,
        blank=True,
        ambit='public',
    )


class SampleAppModel8(models.Model):
    file = FinderFileField(
        models.DO_NOTHING,
        null=True,
        blank=True,
        ambit='public',
    )


class SampleAppModel9(models.Model):
    file = FinderFileField(
        models.SET(REPLACEMENT_FILE_ID),
        null=True,
        blank=True,
        ambit='public',
    )
