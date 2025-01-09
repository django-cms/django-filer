import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'secret_key')

DEBUG = os.getenv('DJANGO_DEBUG') in ['true', 'True', '1', 'yes', 'Yes', 'y', 'on', 'On']

ALLOWED_HOSTS = ['*']

SITE_ID = 1

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'finder',
    'finder.contrib.archive',
    'finder.contrib.audio',
    'finder.contrib.common',
    'finder.contrib.image.pil',
    'finder.contrib.image.svg',
    'finder.contrib.video',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'unittests.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
}]

WSGI_APPLICATION = 'wsgi.application'


if os.getenv('USE_POSTGRES', False) in ['1', 'True', 'true']:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'finder',
            'USER': 'finder',
            'PASSWORD': '',
            'HOST': 'localhost',
            'PORT': 5432,
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'workdir/db.sqlite3',
        },
    }


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

USE_TZ = True

TIME_ZONE = 'UTC'

USE_I18N = True

STATIC_URL = '/static/'

MEDIA_ROOT = Path(os.getenv('DJANGO_MEDIA_ROOT', BASE_DIR / 'workdir/media'))

MEDIA_URL = '/media/'
