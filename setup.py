from setuptools import setup, find_packages
import os

try:
    from setuptest import test
except ImportError:
    print "erro"
    from setuptools.command.test import test

version = __import__('filer').__version__

def read(fname):
    # read the contents of a text file
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "django-filer",
    version = version,
    url = 'http://github.com/stefanfoulis/django-filer',
    license = 'BSD',
    platforms=['OS Independent'],
    description = "A file management application for django that makes handling of files and images a breeze.",
    long_description = read('README.rst'),
    author = 'Stefan Foulis',
    author_email = 'stefan.foulis@gmail.com',
    packages=find_packages(),
    install_requires = (
        'Django>=1.2',
        'easy-thumbnails>=1.0',
        'django-mptt>=0.2.1',
        'django_polymorphic>=0.2',
    ),
    include_package_data=True,
    zip_safe=False,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    cmdclass={'test': test},
    test_suite='setuptest.setuptest.SetupTestSuite',
    tests_require=(
        'django-setuptest',
        'argparse',  # apparently needed by django-setuptest on python 2.6
    ),
)
