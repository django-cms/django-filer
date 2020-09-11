#!/usr/bin/env python
from setuptools import find_packages, setup

from filer import __version__


REQUIREMENTS = [
    'django>=2.2,<4.0',
    'django-mptt>=0.6,<1.0',  # the exact version depends on Django
    'django-polymorphic>=2,<3.1',
    'easy-thumbnails>=2,<3.0',
    'Unidecode>=0.04,<1.2',
]


CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Framework :: Django',
    'Framework :: Django :: 2.2',
    'Framework :: Django :: 3.0',
    'Framework :: Django :: 3.1',
    'Framework :: Django CMS',
    'Framework :: Django CMS :: 3.6',
    'Framework :: Django CMS :: 3.7',
    'Framework :: Django CMS :: 3.8',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    'Topic :: Software Development',
    'Topic :: Software Development :: Libraries',
]


setup(
    name='django-filer',
    version=__version__,
    author='Divio AG',
    author_email='info@divio.ch',
    url='http://github.com/divio/django-filer',
    license='BSD-3-Clause',
    description='A file management application for django that makes handling '
                'of files and images a breeze.',
    long_description=open('README.rst').read(),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS,
    classifiers=CLASSIFIERS,
    test_suite='tests.settings.run',
)
