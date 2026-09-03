===============
Getting started
===============

By the end of this tutorial you will have django-finder installed in a Django project and a
file uploaded through the admin interface. Storages and a first ambit are set up for you, so
there is less to configure than you might expect.

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


Storages: nothing to configure
==============================

Every ambit — django-finder's term for a self-contained folder tree — uses two Django storage
backends: one holding the uploaded originals, one holding everything derived from them, such
as thumbnails and audio or video samples.

You do not have to declare either of them. When ``STORAGES`` contains no ``finder_public``
and no ``finder_public_samples``, django-finder derives both from your ``default`` storage as
the app registry is loaded: the same filesystem root and URL prefix, a subdirectory per name,
the :class:`~finder.storages.FinderSystemStorage` backend and ``allow_overwrite`` enabled.

With Django's defaults that gives you::

    MEDIA_ROOT/finder_public/          served from  MEDIA_URL + finder_public/
    MEDIA_ROOT/finder_public_samples/  served from  MEDIA_URL + finder_public_samples/

which is enough to work through this tutorial. Declare them yourself once you want the files
somewhere else — :doc:`../how-to/configure-storages` covers both the local and the S3 case,
and :doc:`../explanation/thumbnails-and-samples` explains why the split exists.

.. note::

   Deriving them needs a ``FileSystemStorage`` as your ``default``. A remote default has no
   location to put a subdirectory under, so nothing is derived and ``manage.py check``
   reports ``finder.W001``. Declare the two storages explicitly in that case.


Run the migrations
==================

.. code-block:: shell

    ./manage.py migrate

Besides creating the tables, this creates your first ambit, so that the admin and the form
widgets have something to show. It is named by ``FINDER_DEFAULT_AMBIT``, which is ``public``
— the same name a :class:`~finder.models.fields.FinderFileField` refers to when it is
declared without an ``ambit`` argument.

Check that it is there:

.. code-block:: shell

    ./manage.py finder list-ambits

.. code-block:: text

    Slug: public, Name: Public, Site: None, Admin: None,
    Storage: finder_public (FinderSystemStorage),
    Sample Storage: finder_public_samples (FinderSystemStorage)

Its root folder grants read and write to every signed-in user. Narrow that down with the
permission editor in the admin (:doc:`../how-to/grant-permissions`), or take the ambits into
your own hands by setting ``FINDER_CREATE_DEFAULT_AMBIT = False`` before you migrate for the
first time — see :doc:`../how-to/manage-ambits`.


Upload a file
=============

Start the development server and open the admin:

.. code-block:: shell

    ./manage.py runserver

Visit http://localhost:8000/admin/finder/ — it lists the ambits, and following ``Public``
takes you to its root folder. Drag a file from your desktop onto the folder listing, or use
the upload button.

.. todo::

   Add a screenshot of the folder listing after the first upload. The ``_static`` directory
   still holds the django-filer screenshots, which show a different interface.


What next
=========

* :doc:`your-first-file-field` — point one of your own models at a file in the library.
* :doc:`../how-to/grant-permissions` — open the library up to non-superusers.
* :doc:`../explanation/architecture` — what an inode is and why everything is one.
