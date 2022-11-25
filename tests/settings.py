import os
from tempfile import mkdtemp


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HELPER_SETTINGS = {
    'NOSE_ARGS': [
        '-s',
    ],
    'ROOT_URLCONF': 'tests.utils.urls',
    'INSTALLED_APPS': [
        'easy_thumbnails',
        'mptt',
        'filer',
        'tests.utils.test_app',
        'tests.utils.extended_app',
    ],
    'LANGUAGE_CODE': 'en',
    'LANGUAGES': (
        ('en', 'English'),
        ('fr', 'French'),
        ('it', 'Italiano'),
    ),
    'CMS_LANGUAGES': {
        1: [
            {
                'code': 'en',
                'name': 'English',
                'public': True,
            },
            {
                'code': 'it',
                'name': 'Italiano',
                'public': True,
            },
            {
                'code': 'fr',
                'name': 'French',
                'public': True,
            },
        ],
        'default': {
            'hide_untranslated': False,
        },
    },
    'THUMBNAIL_PROCESSORS': (
        'easy_thumbnails.processors.colorspace',
        'easy_thumbnails.processors.autocrop',
        'filer.thumbnail_processors.scale_and_crop_with_subject_location',
        'easy_thumbnails.processors.filters',
    ),
    'FILE_UPLOAD_TEMP_DIR': mkdtemp(),
    'TEMPLATE_DIRS': (os.path.join(BASE_DIR, 'django-filer', 'filer', 'utils', 'templates'),),
    'FILER_CANONICAL_URL': 'test-path/',
    'SECRET_KEY': '__secret__',
    'DEFAULT_AUTO_FIELD': 'django.db.models.AutoField',
}
if os.environ.get('CUSTOM_IMAGE', False):
    HELPER_SETTINGS['FILER_IMAGE_MODEL'] = os.environ.get('CUSTOM_IMAGE')
    HELPER_SETTINGS['INSTALLED_APPS'].append('tests.utils.custom_image')


def run():
    from app_helper import runner
    runner.run('filer')


if __name__ == '__main__':
    run()
