# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
from tempfile import mkdtemp


def gettext(s):
    return s


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HELPER_SETTINGS = {
    'NOSE_ARGS': [
        '-s',
    ],
    'ROOT_URLCONF': 'filer.test_utils.urls',
    'INSTALLED_APPS': [
        'easy_thumbnails',
        'mptt',
        'filer',
        'filer.test_utils.test_app',
        'filer.test_utils.extended_app',
    ],
    'LANGUAGE_CODE': 'en',
    'LANGUAGES': (
        ('en', gettext('English')),
        ('fr_FR', gettext('French')),
        ('it', gettext('Italiano')),
    ),
    'CMS_LANGUAGES': {
        1: [
            {
                'code': 'en',
                'name': gettext('English'),
                'public': True,
            },
            {
                'code': 'it',
                'name': gettext('Italiano'),
                'public': True,
            },
            {
                'code': 'fr_FR',
                'name': gettext('French'),
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
    'TEMPLATE_DIRS': (os.path.join(BASE_DIR, 'django-filer', 'filer', 'test_utils', 'templates'),),
    'FILER_CANONICAL_URL': 'test-path/',
}
if os.environ.get('CUSTOM_IMAGE', False):
    HELPER_SETTINGS['FILER_IMAGE_MODEL'] = os.environ.get('CUSTOM_IMAGE')
    HELPER_SETTINGS['INSTALLED_APPS'].append('filer.test_utils.custom_image')


def run():
    from djangocms_helper import runner
    runner.run('filer')


if __name__ == "__main__":
    run()
