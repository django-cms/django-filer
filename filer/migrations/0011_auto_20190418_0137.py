# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-18 01:37
from __future__ import unicode_literals

from django.db import migrations, models

import sys


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0010_auto_20180414_2058'),
    ]

    options = {
        'editable': False,
    }

    # only for django 11 and py <= 3.4
    if sys.version_info <= (3, 4):
        options['db_index'] = True

    operations = [
        migrations.AlterField(
            model_name='folder',
            name='level',
            field=models.PositiveIntegerField(**options),
        ),
        migrations.AlterField(
            model_name='folder',
            name='lft',
            field=models.PositiveIntegerField(**options),
        ),
        migrations.AlterField(
            model_name='folder',
            name='rght',
            field=models.PositiveIntegerField(**options),
        ),
    ]
