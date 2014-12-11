# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from filer.settings import FILER_IMAGE_MODEL


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0001_initial'),
        migrations.swappable_dependency(FILER_IMAGE_MODEL or 'filer.models.imagemodels.Image'),
    ]

    operations = []
    if not FILER_IMAGE_MODEL:
        operations.append(
            migrations.CreateModel(
                name='Image',
                fields=[
                    ('file_ptr', models.OneToOneField(serialize=False, auto_created=True, to='filer.File', primary_key=True, parent_link=True)),
                    ('_height', models.IntegerField(null=True, blank=True)),
                    ('_width', models.IntegerField(null=True, blank=True)),
                    ('date_taken', models.DateTimeField(verbose_name='date taken', null=True, editable=False, blank=True)),
                    ('default_alt_text', models.CharField(max_length=255, null=True, verbose_name='default alt text', blank=True)),
                    ('default_caption', models.CharField(max_length=255, null=True, verbose_name='default caption', blank=True)),
                    ('author', models.CharField(max_length=255, null=True, verbose_name='author', blank=True)),
                    ('must_always_publish_author_credit', models.BooleanField(default=False, verbose_name='must always publish author credit')),
                    ('must_always_publish_copyright', models.BooleanField(default=False, verbose_name='must always publish copyright')),
                    ('subject_location', models.CharField(default=None, max_length=64, null=True, verbose_name='subject location', blank=True)),
                ],
                options={
                    'verbose_name': 'image',
                    'verbose_name_plural': 'images',
                },
                bases=('filer.file',),
            )
        )
