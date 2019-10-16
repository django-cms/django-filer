# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='owner',
            field=models.ForeignKey(related_name='owned_files', on_delete=django.db.models.deletion.SET_NULL, verbose_name='owner', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='folder',
            name='shared',
            field=models.ManyToManyField(help_text='All the sites which you share this folder with will be able to use this folder on their pages, with all of its assets. However, they will not be able to change, delete or move it, not even add new assets.', related_name='shared', verbose_name='Share folder with sites', to='sites.Site', blank=True),
        ),
    ]
