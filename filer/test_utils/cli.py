# -*- coding: utf-8 -*-
import django
import os

gettext = lambda s: s

import easy_thumbnails
from distutils.version import LooseVersion
if hasattr(easy_thumbnails, 'get_version'):
    ET_2 = LooseVersion(easy_thumbnails.get_version()) > LooseVersion('2.0')
else:
    ET_2 = LooseVersion(easy_thumbnails.VERSION) > LooseVersion('2.0')
DJ_1_7 = LooseVersion(django.get_version()) >= LooseVersion('1.7')

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
        MIDDLEWARE_CLASSES=[
            'django.middleware.http.ConditionalGetMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.middleware.locale.LocaleMiddleware',
            'django.middleware.common.CommonMiddleware',
        ],
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
            ],
        ROOT_URLCONF='filer.test_utils.cli',
    )
    if not DJ_1_7:
        defaults['INSTALLED_APPS'].append('south')
        if ET_2:
            extra['SOUTH_MIGRATION_MODULES'] = {
                'easy_thumbnails': 'easy_thumbnails.south_migrations',
            }
    else:
        extra['MIGRATION_MODULES'] = {
            'filer': 'filer.migrations_django',
        }
    if extra.get('FILER_IMAGE_MODEL', False):
        defaults['INSTALLED_APPS'].append('filer.test_utils.custom_image')

    defaults.update(extra)
    settings.configure(**defaults)
    if not DJ_1_7:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()
        from django.contrib import admin
        admin.autodiscover()
    else:
        django.setup()
