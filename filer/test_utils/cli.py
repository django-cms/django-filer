# -*- coding: utf-8 -*-
import os

gettext = lambda s: s

import easy_thumbnails
from distutils.version import LooseVersion
if hasattr(easy_thumbnails, 'get_version'):
    ET_2 = LooseVersion(easy_thumbnails.get_version()) > LooseVersion('2.0')
else:
    ET_2 = LooseVersion(easy_thumbnails.VERSION) > LooseVersion('2.0')

urlpatterns = []

def configure(**extra):
    from django.conf import settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'filer.test_utils.cli'
    defaults = dict(
        DEBUG=True,
        TEMPLATE_DEBUG=True,
        DATABASE_SUPPORTS_TRANSACTIONS=True,
        DATABASES={
            'default': {'ENGINE': 'django.db.backends.sqlite3'}
        },
        USE_I18N=True,
        MEDIA_ROOT='/media/',
        STATIC_ROOT='/static/',
        MEDIA_URL='/media/',
        STATIC_URL='/static/',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        SECRET_KEY='key',
        TEMPLATE_LOADERS=(
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
            'django.template.loaders.eggs.Loader',
            ),
        SOUTH_TESTS_MIGRATE=True,
        INSTALLED_APPS = [
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django.contrib.staticfiles',
            'easy_thumbnails',
            'mptt',
            'filer',
            'south',
            ],
        ROOT_URLCONF='filer.test_utils.cli',
    )
    if ET_2:
        extra['SOUTH_MIGRATION_MODULES'] = {
            'easy_thumbnails': 'easy_thumbnails.south_migrations',
        }

    defaults.update(extra)
    settings.configure(**defaults)
    from south.management.commands import patch_for_test_db_setup
    patch_for_test_db_setup()
    from django.contrib import admin
    admin.autodiscover()
