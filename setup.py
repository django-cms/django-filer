#!/usr/bin/env python
from setuptools import find_packages, setup

from filer import __version__


REQUIREMENTS = [
    'django>=5.2',
    'django-cte',
]


EXTRA_REQUIREMENTS = {
    "audio": [
        "ffmpeg-python",
        'django-entangled',
    ],
    "image": [
        "Pillow",
        'django-entangled',
    ],
    "svg": [
        "reportlab",
        "svglib",
        'django-entangled',
    ],
    "video": [
        "ffmpeg-python",
        'django-entangled',
    ],
    "s3": [
        "django-storages[s3]",
    ],
}


CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Framework :: Django',
    'Framework :: Django :: 5.2',
    'Framework :: Django :: 6.0',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries',
]


setup(
    name='django-filer',
    version=__version__,
    author='Django CMS Association and contributors',
    author_email='info@django-cms.org',
    maintainer='Django CMS Association and contributors',
    maintainer_email='info@django-cms.org',
    url='https://github.com/django-cms/django-filer',
    license='BSD-3-Clause',
    description='A file management application for django that makes handling '
                'of files and images a breeze.',
    long_description=open('README-Finder.md').read(),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS,
    extras_require=EXTRA_REQUIREMENTS,
    python_requires='>=3.10',
    classifiers=CLASSIFIERS,
    test_suite='tests.settings.run',
)
