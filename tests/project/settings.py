#-*- coding: utf-8 -*-
import os
DEBUG = True
PACKAGE_ROOT = os.path.abspath( os.path.join(os.path.dirname(__file__), '../') )
PROJECT_ROOT = os.path.join(PACKAGE_ROOT, 'project')
TMP_ROOT = os.path.abspath( os.path.join(PACKAGE_ROOT, 'tmp') )
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(TMP_ROOT,'filer_test.db') # won't actually be used. tests under SQLite are run in-memory
INSTALLED_APPS = [
    'filer',
    'mptt',
    'easy_thumbnails',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.staticfiles']
ROOT_URLCONF = 'project.urls'

MEDIA_ROOT = os.path.abspath( os.path.join(TMP_ROOT, 'media') )
MEDIA_URL = '/media/'
STATIC_URL = '/static/'