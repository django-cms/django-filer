==================
Configure storages
==================

Every ambit uses two Django storage backends. The *original* storage holds uploaded payloads;
the *sample* storage holds everything derived from them — image thumbnails, video posters,
audio samples. See :doc:`../explanation/thumbnails-and-samples` for why they are separate.

Both are looked up by name in Django's ``STORAGES`` setting, and are assigned to an ambit when
you create or edit it (:doc:`manage-ambits`).


What you get without configuring anything
=========================================

An ambit refers to ``finder_public`` and ``finder_public_samples`` by default. If ``STORAGES``
declares neither, django-finder derives both from your ``default`` storage while the app
registry loads, in :func:`finder.storages.configure_default_storages`. Each derived entry uses

* the :class:`~finder.storages.FinderSystemStorage` backend,
* the ``location`` and ``base_url`` of your ``default`` storage — falling back to
  ``MEDIA_ROOT`` and ``MEDIA_URL`` — with a subdirectory named after the alias,
* ``allow_overwrite`` enabled, which sample regeneration and sanitizing validators need.

So a project that has configured nothing beyond ``MEDIA_ROOT`` stores originals under
``MEDIA_ROOT/finder_public/`` and samples under ``MEDIA_ROOT/finder_public_samples/``.

The derivation is skipped for any alias you declare yourself, so overriding one and leaving
the other derived works.

.. important::

   A plain ``FileSystemStorage`` is not a substitute for the derived entry, even though it
   would appear to work. :class:`~finder.storages.FinderSystemStorage` shards payloads by
   UUID in its ``path()`` and ``url()`` methods, so an ambit pointed at ``default`` writes
   files where django-finder will not look for them once you correct the configuration.

.. note::

   Deriving needs a ``FileSystemStorage`` as your ``default``. A remote default carries no
   location to put a subdirectory under, so nothing is derived and ``manage.py check``
   reports ``finder.W001``. Declare both storages explicitly in that case.


Local filesystem
================

To put the files somewhere else, declare the entries yourself. Use
:class:`~finder.storages.FinderSystemStorage` rather than Django's ``FileSystemStorage``: it
enforces django-finder's UUID-prefixed path layout and supports overwriting.

.. code-block:: python

    STORAGES = {
        ...
        'finder_public': {
            'BACKEND': 'finder.storages.FinderSystemStorage',
            'OPTIONS': {
                'location': BASE_DIR / 'media/finder_public',
                'base_url': '/media/finder_public/',
                'allow_overwrite': True,
            },
        },
        'finder_public_samples': {
            'BACKEND': 'finder.storages.FinderSystemStorage',
            'OPTIONS': {
                'location': BASE_DIR / 'media/finder_public_samples',
                'base_url': '/media/finder_public_samples/',
                'allow_overwrite': True,
            },
        },
    }


Object storage (S3 and compatible)
==================================

Nothing is derived here — declare both entries. Install the extra and point the backend at
your bucket:

.. code-block:: shell

    pip install -e '.[s3]'

.. code-block:: python

    STORAGES = {
        ...
        'finder_bucket': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                'bucket_name': 'my-media',
                'querystring_auth': False,
                'default_acl': 'public-read',
            },
        },
    }

.. todo::

   Document the constraints object storage puts on django-finder: sample generation copies the
   original to a local temporary file first (``finder.storages.copy_to_local``), and
   ``exists()`` checks on the sample storage cost a round trip per thumbnail. Say what that
   means for latency and for signed URLs.


Moving an ambit to another storage
==================================

Point an existing ambit at different storages with :doc:`manage-ambits`:

.. code-block:: shell

    ./manage.py finder edit-ambit public \
        --values storage=finder_bucket sample_storage=finder_bucket_samples

.. warning::

   Only the ambit's configuration changes. Payloads already written stay where they are, and
   django-finder will look for them in the new storage — so move the files across yourself,
   or do this before anything has been uploaded.


Serving files privately
=======================

.. todo::

   django-filer had a ``secure_downloads`` mechanism with pluggable server backends
   (nginx X-Accel, xsendfile). Document what the equivalent is in django-finder, or state
   plainly that public storage is currently the only supported mode.
