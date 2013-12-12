#-*- coding: utf-8 -*-
import os, filer
DEBUG = True
PACKAGE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(filer.__file__), '..'))
TMP_ROOT = os.path.abspath( os.path.join(PACKAGE_ROOT, 'tmp') )
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(TMP_ROOT,'filer_test.sqlite3'),
        },
    }
INSTALLED_APPS = [
    'filer',
    'mptt',
    'easy_thumbnails',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'cms',
    'menus',
    'south',
    'sekizai',
    'cmsroles',
]

ROOT_URLCONF = 'filer.test_urls'
SITE_ID = 1
MEDIA_ROOT = os.path.abspath( os.path.join(TMP_ROOT, 'media') )
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

USE_TZ = False  # because of a bug in easy-thumbnails 1.0.3

TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    'django.contrib.messages.context_processors.messages',
    "django.core.context_processors.i18n",
    "django.core.context_processors.debug",
    "django.core.context_processors.request",
    "django.core.context_processors.media",
    'django.core.context_processors.csrf',
    "cms.context_processors.media",
    "sekizai.context_processors.sekizai",
    "django.core.context_processors.static",
]

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
)

TEMPLATE_LOADERS = (
    'cmsroles.test_utils.MockLoader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    )

CMS_TEMPLATES = [('cms_mock_template.html', 'cms_mock_template.html')]
SEKIZAI_IGNORE_VALIDATION = True
CMS_MODERATOR = True
CMS_PERMISSION = True

CACHE_BACKEND = 'locmem:///'

SOUTH_TESTS_MIGRATE = False
