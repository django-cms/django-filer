# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import filer.migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0007_auto_20161016_1055'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='file',
            options={'verbose_name': 'file', 'verbose_name_plural': 'files', 'permissions': (('can_publish', 'Can publish'),)},
        ),
        migrations.AddField(
            model_name='file',
            name='publisher_deletion_requested',
            field=models.BooleanField(default=False, db_index=True, editable=False),
        ),
        migrations.AddField(
            model_name='file',
            name='publisher_is_published_version',
            field=models.BooleanField(default=filer.migrations.new_file_is_published_status, db_index=True, editable=False),
        ),
        migrations.AddField(
            model_name='file',
            name='publisher_published_at',
            field=models.DateTimeField(default=None, null=True, editable=False, blank=True),
        ),
        migrations.AddField(
            model_name='file',
            name='publisher_published_version',
            field=models.OneToOneField(related_name='publisher_draft_version', null=True, default=None, editable=False, to='filer.File', blank=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='file_ptr',
            field=models.OneToOneField(parent_link=True, related_name='filer_image_file', primary_key=True, serialize=False, to='filer.File'),
        ),
    ]
