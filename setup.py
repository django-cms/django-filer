from setuptools import setup, find_packages
import os

try:
    from setuptest import test
except ImportError:
    from setuptools.command.test import test

version = __import__('filer').__version__


def read(fname):
    # read the contents of a text file
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

dependency_links = [
    'http://github.com/pbs/django-cms-roles/tarball/master#egg=django-cms-roles-dev',
]

setup(
    name="django-filer",
    version=version,
    url='http://github.com/stefanfoulis/django-filer',
    license='BSD',
    platforms=['OS Independent'],
    description="A file management application for django that makes handling of files and images a breeze.",
    long_description=read('README.rst'),
    author='Stefan Foulis',
    author_email='stefan.foulis@gmail.com',
    packages=find_packages(),
    install_requires=(
        'pytz==2015.4',
        'Django>=1.8,<1.9',
        'easy-thumbnails<=2.2',
        'django-mptt==0.7.4',
        'django_polymorphic<=0.7.1',
        'django-cms-roles>0.7.0.pbs,<0.7.0.pbs.1000',
        'django-cms>=2.3.5pbs,<2.3.5pbs.1000',
        'requests==2.7.0',
    ),
    dependency_links=dependency_links,
    include_package_data=True,
    zip_safe=False,
    classifiers=[
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
        'django-setuptest>=0.1.1',
        'argparse',  # apparently needed by django-setuptest on python 2.6
    ),
)
