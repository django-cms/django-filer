# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0002_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('file_ptr', models.OneToOneField(serialize=False, primary_key=True, to='filer.File', auto_created=True, parent_link=True)),
                ('_height', models.IntegerField(blank=True, null=True)),
                ('_width', models.IntegerField(blank=True, null=True)),
                ('default_alt_text', models.CharField(blank=True, null=True, verbose_name='default alt text', max_length=255)),
                ('default_caption', models.CharField(blank=True, null=True, verbose_name='default caption', max_length=255)),
                ('subject_location', models.CharField(default=None, blank=True, null=True, verbose_name='subject location', max_length=64)),
                ('extra_description', models.TextField()),
            ],
            options={
            },
            bases=('filer.file',),
        ),
    ]
