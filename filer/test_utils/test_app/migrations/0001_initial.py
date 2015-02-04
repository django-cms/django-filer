# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import filer.fields.folder
import filer.fields.file
import filer.fields.image


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MyModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('folder', filer.fields.folder.FilerFolderField(related_name='test_folder', to='filer.Folder')),
                ('general', filer.fields.file.FilerFileField(related_name='test_file', to='filer.File')),
                ('image', filer.fields.image.FilerImageField(related_name='test_image', to='filer.Image')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
