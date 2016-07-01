# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('custom_image', '0002_auto_20160621_1510'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='file_ptr',
            field=models.OneToOneField(to='filer.File', related_name='custom_image_image_file', serialize=False, primary_key=True),
        ),
    ]
