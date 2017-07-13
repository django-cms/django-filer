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
            field=models.OneToOneField(parent_link=True, related_name='extended_app_extimage_file', primary_key=True, serialize=False, to='filer.File'),
        ),
    ]
