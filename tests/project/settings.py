#-*- coding: utf-8 -*-
import os
DEBUG = True
PACKAGE_ROOT = os.path.abspath( os.path.join(os.path.dirname(__file__), '../') )
PROJECT_ROOT = os.path.join(PACKAGE_ROOT, 'project')
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
    'django_jenkins',
]
ROOT_URLCONF = 'project.urls'

MEDIA_ROOT = os.path.abspath( os.path.join(TMP_ROOT, 'media') )
MEDIA_URL = '/media/'
STATIC_URL = '/static/'

# django-jenkins settings
PROJECT_APPS = ['filer'] # list of apps to run tests for
JENKINS_TASKS = (
        #'django_jenkins.tasks.run_pylint',
        #'django_jenkins.tasks.run_pep8',
        'django_jenkins.tasks.with_coverage',
        'django_jenkins.tasks.django_tests',
)
COVERAGE_RCFILE = '.coveragerc'