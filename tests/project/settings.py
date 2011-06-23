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
    'django_jenkins',
]
ROOT_URLCONF = 'project.urls'

MEDIA_ROOT = os.path.abspath( os.path.join(TMP_ROOT, 'media') )
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

# django-jenkins settings
PROJECT_APPS = ['filer'] # list of apps to run tests for
JENKINS_TASKS = (
        #'django_jenkins.tasks.run_pylint', # pylint not working for some weird reason (UTF-8 ValueError)
        'django_jenkins.tasks.with_coverage',
        'django_jenkins.tasks.django_tests',
)