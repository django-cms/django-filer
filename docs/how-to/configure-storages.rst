==================
Configure storages
==================

Every ambit uses two Django storage backends. The *original* storage holds uploaded payloads;
the *sample* storage holds everything derived from them — image thumbnails, video posters,
audio samples. See :doc:`../explanation/thumbnails-and-samples` for why they are separate.

Both are looked up by name in Django's ``STORAGES`` setting, and are assigned to an ambit when
you create or edit it (:doc:`manage-ambits`).


Local filesystem
================

Use :class:`~finder.storages.FinderSystemStorage` rather than Django's
``FileSystemStorage``: it enforces django-finder's UUID-prefixed path layout and supports
overwriting.

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

Install the extra and point the backend at your bucket:

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


Serving files privately
=======================

.. todo::

   django-filer had a ``secure_downloads`` mechanism with pluggable server backends
   (nginx X-Accel, xsendfile). Document what the equivalent is in django-finder, or state
   plainly that public storage is currently the only supported mode.
