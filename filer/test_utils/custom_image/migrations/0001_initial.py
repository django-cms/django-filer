# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('file_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='filer.File')),
                ('_height', models.IntegerField(null=True, blank=True)),
                ('_width', models.IntegerField(null=True, blank=True)),
                ('default_alt_text', models.CharField(max_length=255, null=True, verbose_name='default alt text', blank=True)),
                ('default_caption', models.CharField(max_length=255, null=True, verbose_name='default caption', blank=True)),
                ('subject_location', models.CharField(default=None, max_length=64, null=True, verbose_name='subject location', blank=True)),
                ('extra_description', models.TextField()),
            ],
            options={
            },
            bases=('filer.file',),
        ),
    ]
