# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from filer.settings import FILER_IMAGE_MODEL


class Migration(migrations.Migration):


    dependencies = [
        ('filer', '0004_auto_20160328_1434'),
    ]

    operations = []
    if not FILER_IMAGE_MODEL:
        operations.append(
            migrations.AlterField(
                model_name='image',
                name='subject_location',
                field=models.CharField(blank=True, default='', max_length=64, verbose_name='subject location'),
            ),
        )
