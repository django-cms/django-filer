# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('extended_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extimage',
            name='file_ptr',
            field=models.OneToOneField(serialize=False, primary_key=True, related_name='extended_app_extimage_file', to='filer.File'),
        ),
        migrations.AlterField(
            model_name='extimage',
            name='subject_location',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='subject location'),
        ),
    ]
