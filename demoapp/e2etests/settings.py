"""
Settings used by the end-to-end test suite.

These build upon the regular ``demoapp`` settings, but keep their state in
``workdir/e2e`` so that running the browser tests never clobbers the database or
the media files of a local development server.

Run the suite with::

    pytest demoapp/e2etests --ds=demoapp.e2etests.settings
"""

from demoapp.settings import *  # noqa: F401,F403
from demoapp.settings import BASE_DIR


E2E_DIR = BASE_DIR / 'workdir/e2e'

ROOT_URLCONF = 'demoapp.e2etests.urls'

DATABASES = {
    'default': {
        **DATABASES['default'],  # noqa: F405
    },
}
if DATABASES['default']['ENGINE'].endswith('sqlite3'):
    # ``live_server`` runs the server in a separate thread, so an in-memory
    # database is not shared with the test process.
    DATABASES['default']['NAME'] = E2E_DIR / 'e2e.sqlite3'
    DATABASES['default'].setdefault('OPTIONS', {})['timeout'] = 20

MEDIA_ROOT = E2E_DIR / 'media'

# Point the ambit storages at the end-to-end working directory. Their ``base_url``
# stays below ``MEDIA_URL`` so that ``demoapp.e2etests.urls`` can serve them.
STORAGES = {
    **STORAGES,  # noqa: F405
    'finder_demo': {
        'BACKEND': 'finder.storages.FinderSystemStorage',
        'OPTIONS': {
            'location': MEDIA_ROOT / 'finder_demo',
            'base_url': '/media/finder_demo/',
            'allow_overwrite': True,
        },
    },
    'finder_demo_samples': {
        'BACKEND': 'finder.storages.FinderSystemStorage',
        'OPTIONS': {
            'location': MEDIA_ROOT / 'finder_demo_samples',
            'base_url': '/media/finder_demo_samples/',
            'allow_overwrite': True,
        },
    },
}

# Speed up the login performed by ``AutoLoginMiddleware``.
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
