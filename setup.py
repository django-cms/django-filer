# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from setuptools import setup, find_packages
import os

version = __import__('filer').__version__


def read(fname):
    # read the contents of a text file
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="django-filer",
    version=version,
    url='http://github.com/stefanfoulis/django-filer',
    license='BSD',
    platforms=['OS Independent'],
    description="A file management application for django that makes handling "
                "of files and images a breeze.",
    long_description = read('README.rst'),
    author='Stefan Foulis',
    author_email='stefan@foulis.ch',
    packages=find_packages(),
    install_requires=(
        'Django>=1.5',
        'easy-thumbnails>=1.0',
        'django-mptt>=0.6',
        'django_polymorphic>=0.7',
        'Unidecode>=0.04',
    ),
    include_package_data=True,
    zip_safe=False,
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Framework :: Django',
        'Framework :: Django :: 1.5',
        'Framework :: Django :: 1.6',
        'Framework :: Django :: 1.7',
        'Framework :: Django :: 1.8',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='cms_helper.run',
    tests_require=(
        'argparse',  # needed on python 2.6
        'south',
    ),
)
