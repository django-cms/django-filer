#!/usr/bin/env python
from setuptools import find_packages, setup

from filer import __version__


REQUIREMENTS = [
    'django>=2.2,<5',
    'django-mptt',
    'django-polymorphic',
    'easy-thumbnails[svg]',
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
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Framework :: Django',
    'Framework :: Django :: 2.2',
    'Framework :: Django :: 3.0',
    'Framework :: Django :: 3.1',
    'Framework :: Django :: 3.2',
    'Framework :: Django :: 4.0',
    'Framework :: Django :: 4.1',
    'Framework :: Django CMS',
    'Framework :: Django CMS :: 3.6',
    'Framework :: Django CMS :: 3.7',
    'Framework :: Django CMS :: 3.8',
    'Framework :: Django CMS :: 3.9',
    'Framework :: Django CMS :: 3.10',
    'Framework :: Django CMS :: 3.11',
    'Framework :: Django CMS :: 4.0',
    'Framework :: Django CMS :: 4.1',
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
    maintainer='Django CMS Association and contributors',
    maintainer_email='info@django-cms.org',
    url='https://github.com/django-cms/django-filer',
    license='BSD-3-Clause',
    description='A file management application for django that makes handling '
                'of files and images a breeze.',
    long_description=open('README.rst').read(),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=REQUIREMENTS,
    python_requires='>=3.6',
    classifiers=CLASSIFIERS,
    test_suite='tests.settings.run',
)
