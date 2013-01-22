# -*- coding: utf-8 -*-
from distutils.version import LooseVersion
import django
import os

gettext = lambda s: s

urlpatterns = []
DJANGO_1_3 = LooseVersion(django.get_version()) < LooseVersion('1.4')

def configure(**extra):
    from django.conf import settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'filer.test_utils.cli'
    defaults = dict(
        CACHE_BACKEND='locmem:///',
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
        ADMIN_MEDIA_PREFIX='/static/admin/',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        SECRET_KEY='key',
        TEMPLATE_LOADERS=(
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
            'django.template.loaders.eggs.Loader',
            ),
#        TEMPLATE_CONTEXT_PROCESSORS=[
#            "django.contrib.auth.context_processors.auth",
#            'django.contrib.messages.context_processors.messages',
#            "django.core.context_processors.i18n",
#            "django.core.context_processors.debug",
#            "django.core.context_processors.request",
#            "django.core.context_processors.media",
#            'django.core.context_processors.csrf',
#            "django.core.context_processors.static",
#            ],
#        TEMPLATE_DIRS=[
#            os.path.abspath(os.path.join(os.path.dirname(__file__), 'project', 'templates'))
#        ],
#        MIDDLEWARE_CLASSES=[
#            'django.contrib.sessions.middleware.SessionMiddleware',
#            'django.contrib.auth.middleware.AuthenticationMiddleware',
#            'django.contrib.messages.middleware.MessageMiddleware',
#            'django.middleware.csrf.CsrfViewMiddleware',
#            'django.middleware.locale.LocaleMiddleware',
#            'django.middleware.doc.XViewMiddleware',
#            'django.middleware.common.CommonMiddleware',
#            'django.middleware.transaction.TransactionMiddleware',
#            'django.middleware.cache.FetchFromCacheMiddleware',
#            'cms.middleware.user.CurrentUserMiddleware',
#            'cms.middleware.page.CurrentPageMiddleware',
#            'cms.middleware.toolbar.ToolbarMiddleware',
#            ],
        INSTALLED_APPS = [
            'filer',
            'mptt',
            'easy_thumbnails',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django.contrib.staticfiles',
            ],
        ROOT_URLCONF='filer.test_utils.cli',
    )
#    if DJANGO_1_3:
#        defaults['INSTALLED_APPS'].append("i18nurls")
#        defaults['MIDDLEWARE_CLASSES'][4] = 'i18nurls.middleware.LocaleMiddleware'
#    else:
#        from django.utils.functional import empty
#        settings._wrapped = empty
    defaults.update(extra)
    settings.configure(**defaults)
#    from south.management.commands import patch_for_test_db_setup
#    patch_for_test_db_setup()
    from django.contrib import admin
    admin.autodiscover()