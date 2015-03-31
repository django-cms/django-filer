# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from filer.settings import FILER_IMAGE_MODEL
import filer.fields.file
import filer.fields.image
import filer.validators


class Migration(migrations.Migration):

    if FILER_IMAGE_MODEL:
        dependencies = [
            ('filer', '0002_auto_20150606_2003'), 
            ('custom_image', '0001_initial'),
        ]
    else:
        dependencies = [
            ('filer', '0002_auto_20150606_2003'), 
        ]

    operations = [
        migrations.CreateModel(
            name='Example',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=100, verbose_name='title')),
                ('document_choose_or_browse', filer.fields.image.FilerImageField(related_name='documents+', validators=[filer.validators.FileMimetypeValidator(['application/msword', 'application/pdf', 'application/vnd.ms-excel', 'application/vnd.ms-powerpoint', 'application/vnd.oasis.opendocument.text', 'application/vnd.oasis.opendocument.spreadsheet', 'application/vnd.oasis.opendocument.presentation', 'text/csv'])], to='filer.Image', blank=True, help_text='CSV, PDF, ODT, DOC...', null=True, verbose_name='document')),
                ('file_choose_only', filer.fields.file.FilerFileField(related_name='files+', verbose_name='file', blank=True, to='filer.File', null=True)),
                ('illustration_browse_only', filer.fields.image.FilerImageField(related_name='illustrations+', verbose_name='illustration', blank=True, to='filer.Image', null=True)),
            ],
            options={
                'verbose_name': 'example',
                'verbose_name_plural': 'examples',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExampleGalleryElement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order', models.PositiveIntegerField(default=0, verbose_name='order', blank=True)),
                ('example', models.ForeignKey(related_name='gallery_elements', verbose_name='example', to='thirdparty_app.Example')),
                ('image', filer.fields.image.FilerImageField(related_name='images+', validators=[filer.validators.FileMimetypeValidator(['image/svg+xml', 'image/jpeg', 'image/png', 'image/gif'])], to='filer.Image', blank=True, null=True, verbose_name='image')),
            ],
            options={
                'ordering': ('example__pk', 'order'),
                'verbose_name': 'gallery',
                'verbose_name_plural': 'galleries',
            },
            bases=(models.Model,),
        ),
    ]
