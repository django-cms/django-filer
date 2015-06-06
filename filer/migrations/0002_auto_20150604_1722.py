# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import filer.fields.file
from django.conf import settings
import filer.fields.permission_set


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('filer', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('who', models.CharField(default=b'group', max_length=32, choices=[(b'everyone', b'Everyone'), (b'user', b'User'), (b'group', b'Group')])),
                ('subject', models.CharField(max_length=32, choices=[(b'root', b'Root'), (b'folder', b'Folder'), (b'file', b'File')])),
                ('can_read', models.SmallIntegerField(default=None, null=True, verbose_name='can read', blank=True, choices=[(1, 'allow'), (0, 'deny')])),
                ('can_edit', models.SmallIntegerField(default=None, null=True, verbose_name='can edit', blank=True, choices=[(1, 'allow'), (0, 'deny')])),
                ('file', filer.fields.file.FilerFileField(related_name='permission_set', blank=True, to='filer.File', null=True)),
                ('folder', models.ForeignKey(related_name='permission_set', blank=True, to='filer.Folder', null=True)),
                ('group', models.ForeignKey(related_name='filer_permissions_set', blank=True, to='auth.Group', null=True)),
                ('user', models.ForeignKey(related_name='filer_permission_set', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name': 'permission',
                'verbose_name_plural': 'permissions',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='file',
            name='who_can_edit',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='who_can_edit_local',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='who_can_read',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='file',
            name='who_can_read_local',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='folder',
            name='who_can_edit',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='folder',
            name='who_can_edit_local',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='folder',
            name='who_can_read',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='folder',
            name='who_can_read_local',
            field=filer.fields.permission_set.PermissionSetField(),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='file',
            name='polymorphic_ctype',
            field=models.ForeignKey(related_name='polymorphic_filer.file_set+', editable=False, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
    ]
