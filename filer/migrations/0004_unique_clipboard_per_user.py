# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('filer', '0003_delete_duplicate_clipboards'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clipboard',
            name='user',
            field=models.OneToOneField(related_name='filer_clipboard', verbose_name='user', to=settings.AUTH_USER_MODEL),
        ),
    ]
