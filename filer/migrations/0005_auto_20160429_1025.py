# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):


    dependencies = [
        ('filer', '0004_auto_20160328_1434'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='subject_location',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='subject location'),
        ),
    ]
