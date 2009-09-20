import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "django-filer",
    version = "0.1",
    url = 'http://github.com/stefanfoulis/django-filer',
    license = 'BSD',
    description = "A file management application for django that makes handling of files and images a breeze.",
    long_description = read('README'),
    author = 'Stefan Foulis',
    author_email = 'stefan.foulis@gmail.com',
    packages = find_packages('src'),
    package_dir = {'': 'src'},
    install_requires = ['setuptools','django'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)