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
            field=models.OneToOneField(primary_key=True, serialize=False, related_name='extended_app_extimage_file', parent_link=True, to='filer.File'),
        ),
    ]
