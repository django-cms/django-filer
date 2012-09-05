#-*- coding: utf-8 -*-
import os
DEBUG = True
PACKAGE_ROOT = os.path.abspath( os.path.dirname(__file__) )
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
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
]

ROOT_URLCONF = 'test_urls'

MEDIA_ROOT = os.path.abspath( os.path.join(TMP_ROOT, 'media') )
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

USE_TZ = False  # because of a bug in easy-thumbnails 1.0.3
