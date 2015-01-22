# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import filer.fields.multistorage_file
import filer.models.mixins
from filer.settings import FILER_IMAGE_MODEL
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
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
                ('file', filer.fields.multistorage_file.MultiStorageFileField(max_length=255, upload_to=filer.fields.multistorage_file.generate_filename_multistorage, null=True, verbose_name='file', blank=True)),
                ('_file_size', models.IntegerField(null=True, verbose_name='file size', blank=True)),
                ('sha1', models.CharField(default='', max_length=40, verbose_name='sha1', blank=True)),
                ('has_all_mandatory_data', models.BooleanField(default=False, verbose_name='has all mandatory data', editable=False)),
                ('original_filename', models.CharField(max_length=255, null=True, verbose_name='original filename', blank=True)),
                ('name', models.CharField(default='', max_length=255, verbose_name='name', blank=True)),
                ('description', models.TextField(null=True, verbose_name='description', blank=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='uploaded at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('is_public', models.BooleanField(default=True, help_text='Disable any permission checking for this file. File will be publicly accessible to anyone.', verbose_name='Permissions disabled')),
            ],
            options={
                'verbose_name': 'file',
                'verbose_name_plural': 'files',
            },
            bases=(models.Model, filer.models.mixins.IconsMixin),
        ),
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='uploaded at')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='modified at')),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('owner', models.ForeignKey(related_name='filer_owned_folders', verbose_name='owner', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('parent', models.ForeignKey(related_name='children', verbose_name='parent', blank=True, to='filer.Folder', null=True)),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Folder',
                'verbose_name_plural': 'Folders',
                'permissions': (('can_use_directory_listing', 'Can use directory listing'),),
            },
            bases=(models.Model, filer.models.mixins.IconsMixin),
        ),
        migrations.CreateModel(
            name='FolderPermission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.SmallIntegerField(default=0, verbose_name='type', choices=[(0, 'all items'), (1, 'this item only'), (2, 'this item and all children')])),
                ('everybody', models.BooleanField(default=False, verbose_name='everybody')),
                ('can_edit', models.SmallIntegerField(default=None, null=True, verbose_name='can edit', blank=True, choices=[(1, 'allow'), (0, 'deny')])),
                ('can_read', models.SmallIntegerField(default=None, null=True, verbose_name='can read', blank=True, choices=[(1, 'allow'), (0, 'deny')])),
                ('can_add_children', models.SmallIntegerField(default=None, null=True, verbose_name='can add children', blank=True, choices=[(1, 'allow'), (0, 'deny')])),
                ('folder', models.ForeignKey(verbose_name='folder', blank=True, to='filer.Folder', null=True)),
                ('group', models.ForeignKey(related_name='filer_folder_permissions', verbose_name='group', blank=True, to='auth.Group', null=True)),
                ('user', models.ForeignKey(related_name='filer_folder_permissions', verbose_name='user', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name': 'folder permission',
                'verbose_name_plural': 'folder permissions',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='folder',
            unique_together=set([('parent', 'name')]),
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
            field=models.ForeignKey(related_name='owned_files', verbose_name='owner', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_filer.file_set', editable=False, to='contenttypes.ContentType', null=True),
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
