===============
Getting started
===============

By the end of this tutorial you will have django-finder installed in a Django project, a first
ambit created, and a file uploaded through the admin interface.

You need a working Django project running Django 5.2 or later, and Python 3.11 or later.
django-finder has been tested against SQLite and PostgreSQL; it should also work on MariaDB
and MySQL.


Install the package
===================

django-finder is not on PyPI yet, so install it from GitHub:

.. code-block:: shell

    git clone https://github.com/django-cms/django-filer.git
    cd django-filer
    git switch finder
    pip install -e .

.. todo::

   Confirm the intended install command. The old README used ``pip install --no-deps -e .``,
   which installs no dependencies at all — including none of the optional extras. Decide
   whether the tutorial should install an extra (for example ``pip install -e '.[image]'``)
   so that the reader can actually upload the image used later in this tutorial.


Add the apps to your project
============================

django-finder is split into a core app and one contrib app per family of file types. Add the
core app and whichever contrib apps you need:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'finder',
        'finder.contrib.archive',  # zip, tar, tar.gz, tar.bz2, tar.xz
        'finder.contrib.audio',  # mp3, ogg, wav, opus
        'finder.contrib.common',  # PDF, spreadsheets, text, office documents
        'finder.contrib.image.pil',  # avif, gif, jpeg, png, webp
        'finder.contrib.image.svg',  # svg
        'finder.contrib.video',  # mp4
        ...
    ]

Each contrib app brings its own dependencies. :doc:`../how-to/install-file-type-support`
lists what each one needs.


Configure the two storage backends
==================================

Every ambit — django-finder's term for a self-contained folder tree — needs two Django
storage backends: one holding the uploaded originals, one holding everything derived from
them, such as thumbnails and audio or video samples.

.. code-block:: python

    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
        'finder_public': {
            'BACKEND': 'finder.storages.FinderSystemStorage',
            'OPTIONS': {
                'location': '/path/to/your/media/finder_public',
                'base_url': '/media/finder_public/',
                'allow_overwrite': True,
            },
        },
        'finder_public_samples': {
            'BACKEND': 'finder.storages.FinderSystemStorage',
            'OPTIONS': {
                'location': '/path/to/your/media/finder_public_samples',
                'base_url': '/media/finder_public_samples/',
                'allow_overwrite': True,
            },
        },
    }

:doc:`../explanation/thumbnails-and-samples` explains why the split exists, and
:doc:`../how-to/configure-storages` covers object storage such as S3.


Run the migrations
==================

.. code-block:: shell

    ./manage.py migrate


Create your first ambit
=======================

An ambit holds one root folder, one trash folder per user, and its own pair of storage
backends. There is no default ambit — you must create one before the admin has anything to
show:

.. code-block:: shell

    ./manage.py finder add-ambit default \
        --values name="Media Library" \
                 storage=finder_public \
                 sample_storage=finder_public_samples

Check that it exists:

.. code-block:: shell

    ./manage.py finder list-ambits


Upload a file
=============

Start the development server and open the admin:

.. code-block:: shell

    ./manage.py runserver

Visit http://localhost:8000/admin/finder/foldermodel/ — you are redirected to the root folder
of your new ambit. Drag a file from your desktop onto the folder listing, or use the upload
button.

.. todo::

   Add a screenshot of the folder listing after the first upload. The ``_static`` directory
   still holds the django-filer screenshots, which show a different interface.


What next
=========

* :doc:`your-first-file-field` — point one of your own models at a file in the library.
* :doc:`../how-to/grant-permissions` — open the library up to non-superusers.
* :doc:`../explanation/architecture` — what an inode is and why everything is one.
