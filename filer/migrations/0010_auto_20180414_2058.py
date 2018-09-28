# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0009_auto_20171220_1635'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='file_ptr',
            field=models.OneToOneField(primary_key=True, serialize=False, related_name='filer_image_file', parent_link=True, to='filer.File', on_delete=django.db.models.deletion.CASCADE),
        ),
    ]
