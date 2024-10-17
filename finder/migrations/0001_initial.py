# Generated by Django 4.2.15 on 2024-10-11 09:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import finder.models.file
import finder.models.inode
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FolderModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255, validators=[finder.models.inode.filename_validator], verbose_name='Name')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('last_modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified at')),
                ('meta_data', models.JSONField(blank=True, default=dict)),
                ('owner', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
                ('parent', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='finder.foldermodel', verbose_name='Folder')),
            ],
            options={
                'verbose_name': 'Folder',
                'verbose_name_plural': 'Folders',
                'default_permissions': ['read', 'write'],
            },
        ),
        migrations.CreateModel(
            name='Label',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Name')),
                ('color', models.CharField(default='#000000', max_length=7, verbose_name='Color')),
            ],
            options={
                'verbose_name': 'Label',
                'verbose_name_plural': 'Labels',
            },
        ),
        migrations.CreateModel(
            name='RealmModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(editable=False, max_length=200, null=True, verbose_name='Slug')),
                ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sites.site', verbose_name='Site')),
            ],
            options={
                'ordering': ['site', 'slug'],
            },
        ),
        migrations.CreateModel(
            name='PinnedFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('folder', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='pinned_folders', to='finder.foldermodel')),
                ('owner', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ImageModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255, validators=[finder.models.inode.filename_validator], verbose_name='Name')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('last_modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified at')),
                ('meta_data', models.JSONField(blank=True, default=dict)),
                ('file_name', models.CharField(editable=False, max_length=255, verbose_name='File name')),
                ('file_size', models.BigIntegerField(editable=False, verbose_name='Size')),
                ('sha1', models.CharField(blank=True, default='', editable=False, max_length=40, verbose_name='SHA1-hash')),
                ('mime_type', models.CharField(db_index=True, default='application/octet-stream', editable=False, help_text='MIME-type of uploaded content', max_length=255, validators=[finder.models.file.mimetype_validator], verbose_name='MIME-type')),
                ('width', models.SmallIntegerField(default=0)),
                ('height', models.SmallIntegerField(default=0)),
                ('labels', models.ManyToManyField(blank=True, related_name='+', to='finder.label', verbose_name='Labels')),
                ('owner', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
                ('parent', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='finder.foldermodel', verbose_name='Folder')),
            ],
        ),
        migrations.AddField(
            model_name='foldermodel',
            name='realm',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='finder.realmmodel', verbose_name='Realm'),
        ),
        migrations.CreateModel(
            name='FileModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(db_index=True, max_length=255, validators=[finder.models.inode.filename_validator], verbose_name='Name')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('last_modified_at', models.DateTimeField(auto_now=True, verbose_name='Modified at')),
                ('meta_data', models.JSONField(blank=True, default=dict)),
                ('file_name', models.CharField(editable=False, max_length=255, verbose_name='File name')),
                ('file_size', models.BigIntegerField(editable=False, verbose_name='Size')),
                ('sha1', models.CharField(blank=True, default='', editable=False, max_length=40, verbose_name='SHA1-hash')),
                ('mime_type', models.CharField(db_index=True, default='application/octet-stream', editable=False, help_text='MIME-type of uploaded content', max_length=255, validators=[finder.models.file.mimetype_validator], verbose_name='MIME-type')),
                ('labels', models.ManyToManyField(blank=True, related_name='+', to='finder.label', verbose_name='Labels')),
                ('owner', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
                ('parent', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='finder.foldermodel', verbose_name='Folder')),
            ],
            options={
                'verbose_name': 'File',
                'verbose_name_plural': 'Files',
                'abstract': False,
                'default_permissions': [],
            },
        ),
        migrations.CreateModel(
            name='DiscardedInode',
            fields=[
                ('inode', models.UUIDField(primary_key=True, serialize=False)),
                ('deleted_at', models.DateTimeField(auto_now_add=True, verbose_name='Deleted at')),
                ('previous_parent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='finder.foldermodel')),
            ],
        ),
        migrations.CreateModel(
            name='ArchiveModel',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('finder.filemodel',),
        ),
        migrations.CreateModel(
            name='AudioFileModel',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('finder.filemodel',),
        ),
        migrations.CreateModel(
            name='PDFFileModel',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('finder.filemodel',),
        ),
        migrations.CreateModel(
            name='PILImageModel',
            fields=[
            ],
            options={
                'verbose_name': 'Web Image',
                'verbose_name_plural': 'Web Images',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('finder.imagemodel',),
        ),
        migrations.CreateModel(
            name='SpreadsheetModel',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('finder.filemodel',),
        ),
        migrations.CreateModel(
            name='SVGImageModel',
            fields=[
            ],
            options={
                'verbose_name': 'SVG Image',
                'verbose_name_plural': 'SVG Images',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('finder.imagemodel',),
        ),
        migrations.CreateModel(
            name='VideoFileModel',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('finder.filemodel',),
        ),
        migrations.AddConstraint(
            model_name='realmmodel',
            constraint=models.UniqueConstraint(fields=('site', 'slug'), name='unique_site'),
        ),
        migrations.AddConstraint(
            model_name='foldermodel',
            constraint=models.UniqueConstraint(fields=('parent', 'name'), name='unique_realm'),
        ),
    ]