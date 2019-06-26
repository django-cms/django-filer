# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('extended_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extimage',
            name='file_ptr',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, related_name='extended_app_extimage_file', serialize=False, to='filer.File'),
        ),
        migrations.AlterModelOptions(
            name='extimage',
            options={'default_manager_name': 'objects'},
        ),
        migrations.AlterModelOptions(
            name='video',
            options={'default_manager_name': 'objects'},
        ),
    ]
