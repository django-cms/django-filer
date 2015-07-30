# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import filer.fields.multistorage_file
import filer.models.mixins
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Clipboard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'verbose_name': 'clipboard',
                'verbose_name_plural': 'clipboards',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ClipboardItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('clipboard', models.ForeignKey(verbose_name='clipboard', to='filer.Clipboard')),
            ],
            options={
                'verbose_name': 'clipboard item',
                'verbose_name_plural': 'clipboard items',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('file', filer.fields.multistorage_file.MultiStorageFileField(upload_to=filer.fields.multistorage_file.generate_filename_multistorage, max_length=255, blank=True, null=True, verbose_name='file', db_index=True)),
                ('_file_size', models.IntegerField(null=True, verbose_name='file size', blank=True)),
                ('sha1', models.CharField(default=b'', max_length=40, verbose_name='sha1', blank=True)),
                ('has_all_mandatory_data', models.BooleanField(default=False, verbose_name='has all mandatory data', editable=False)),
                ('original_filename', models.CharField(max_length=255, null=True, verbose_name='original filename', blank=True)),
                ('name', models.CharField(help_text='Change the FILE name for an image in the cloud storage system; be sure to include the extension (.jpg or .png, for example) to ensure asset remains valid.', max_length=255, null=True, verbose_name='file name', blank=True)),
                ('title', models.CharField(help_text='Used in the Photo Gallery plugin as a title or name for an image; not displayed via the image plugin.', max_length=255, null=True, verbose_name='name', blank=True)),
                ('description', models.TextField(help_text='Used in the Photo Gallery plugin as a description; not displayed via the image plugin.', null=True, verbose_name='description', blank=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='uploaded at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('is_public', models.BooleanField(default=True, help_text='Disable any permission checking for this file. File will be publicly accessible to anyone.', verbose_name='Permissions disabled')),
                ('restricted', models.BooleanField(default=False, help_text='If this box is checked, Editors and Writers will still be able to view the asset, add it to a plugin or smart snippet but will not be able to delete or modify the current version of the asset.', verbose_name='Restrict Editors and Writers from being able to edit or delete this asset')),
                ('deleted_at', models.DateTimeField(verbose_name='deleted at', null=True, editable=False, blank=True)),
            ],
            options={
                'verbose_name': 'file',
                'verbose_name_plural': 'files',
            },
            bases=(models.Model, filer.models.mixins.IconsMixin),
        ),
        migrations.CreateModel(
            name='Archive',
            fields=[
                ('file_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='filer.File')),
            ],
            options={
                'verbose_name': 'archive',
                'verbose_name_plural': 'archives',
            },
            bases=('filer.file',),
        ),
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='uploaded at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('folder_type', models.IntegerField(default=0, choices=[(0, b'Site Folder'), (1, b'Core Folder')])),
                ('restricted', models.BooleanField(default=False, help_text='If this box is checked, Editors and Writers will still be able to view this folder assets, add them to a plugin or smart snippet but will not be able to delete or modify the current version of the assets.', verbose_name='Restrict Editors and Writers from being able to edit or delete anything from this folder')),
                ('deleted_at', models.DateTimeField(verbose_name='deleted at', null=True, editable=False, blank=True)),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('owner', models.ForeignKey(related_name='filer_owned_folders', on_delete=django.db.models.deletion.SET_NULL, verbose_name=b'owner', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('parent', models.ForeignKey(related_name='children', verbose_name=b'parent', blank=True, to='filer.Folder', null=True)),
                ('shared', models.ManyToManyField(related_name='shared', to='sites.Site', blank=True, help_text='All the sites which you share this folder with will be able to use this folder on their pages, with all of its assets. However, they will not be able to change, delete or move it, not even add new assets.', null=True, verbose_name='Share folder with sites')),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='sites.Site', help_text='Select the site which will use this folder.', null=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Folder',
                'verbose_name_plural': 'Folders',
                'permissions': (('can_use_directory_listing', 'Can use directory listing'), ('can_restrict_operations', 'Can restrict files or folders')),
            },
            bases=(models.Model, filer.models.mixins.IconsMixin),
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('file_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='filer.File')),
                ('_height', models.IntegerField(null=True, blank=True)),
                ('_width', models.IntegerField(null=True, blank=True)),
                ('date_taken', models.DateTimeField(verbose_name='date taken', null=True, editable=False, blank=True)),
                ('default_alt_text', models.CharField(help_text='Describes the essence of the image for users who have images turned off in their browser, or are visually impaired and using a screen reader; and it is used to identify images to search engines.', max_length=255, null=True, verbose_name='default alt text', blank=True)),
                ('default_caption', models.CharField(help_text='Caption text is displayed directly below an image plugin to add context; there is a 140-character limit, including spaces; for images fewer than 200 pixels wide, the caption text is only displayed on hover.', max_length=255, null=True, verbose_name='default caption', blank=True)),
                ('default_credit', models.CharField(help_text='Credit text gives credit to the owner or licensor of an image; it is displayed below the image plugin, or below the caption text on an image plugin, if that option is selected; it is displayed along the bottom of an image in the photo gallery plugin; there is a 30-character limit, including spaces.', max_length=255, null=True, verbose_name='default credit text', blank=True)),
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
        ),
        migrations.AddField(
            model_name='file',
            name='folder',
            field=models.ForeignKey(related_name='all_files', verbose_name='folder', blank=True, to='filer.Folder', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='owner',
            field=models.ForeignKey(related_name='owned_files', on_delete=django.db.models.deletion.SET_NULL, verbose_name='uploaded by', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_filer.file_set+', editable=False, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='clipboarditem',
            name='file',
            field=models.ForeignKey(verbose_name='file', to='filer.File'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='clipboard',
            name='files',
            field=models.ManyToManyField(related_name='in_clipboards', verbose_name='files', through='filer.ClipboardItem', to='filer.File'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='clipboard',
            name='user',
            field=models.ForeignKey(related_name='filer_clipboards', verbose_name='user', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
