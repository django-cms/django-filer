from setuptools import setup, find_packages
import os

version = __import__('filer').__version__

media_files = []
for dir in ['filer/media','filer/templates']:
    for dirpath, dirnames, filenames in os.walk(dir):
        media_files.append([dirpath, [os.path.join(dirpath, f) for f in filenames]])

def read(fname):
    # read the contents of a text file
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

install_requires = [
    'setuptools',
    'easy-thumbnails',
    'django-mptt>=0.2.1',
]

setup(
    name = "django-filer-easy-thumbnails",
    version = version,
    url = 'http://github.com/stefanfoulis/django-filer',
    license = 'BSD',
    platforms=['OS Independent'],
    description = "A file management application for django that makes handling of files and images a breeze.",
    long_description = read('README.rst'),
    author = 'Stefan Foulis',
    author_email = 'stefan.foulis@gmail.com',
    packages=find_packages(),
    install_requires = install_requires,
    package_data={
        '': ['*.txt', '*.rst',],
    },
    package_dir = {
        'filer':'filer',
    },
    data_files = media_files,
    zip_safe=False,
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