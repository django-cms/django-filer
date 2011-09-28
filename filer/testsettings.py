import os
DEBUG = True
PACKAGE_ROOT = os.path.abspath( os.path.join(os.path.dirname(__file__), '../') )
PROJECT_ROOT = os.path.join(PACKAGE_ROOT, 'filer')
TMP_ROOT = os.path.abspath( os.path.join(PACKAGE_ROOT, 'tmp') )
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'db.sqlite3'
INSTALLED_APPS = [
    'filer',
    'mptt',
    'easy_thumbnails',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.sessions',]
ROOT_URLCONF = 'filer.testurls'

MEDIA_ROOT = os.path.abspath( os.path.join(TMP_ROOT, 'media') )
MEDIA_URL = '/media/'