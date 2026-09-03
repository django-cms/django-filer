========
Settings
========

All settings are optional and are read from your project's ``settings.py``. django-finder
reads them through :mod:`finder.settings`, which falls back to Django's own settings for any
name it does not define itself.


``FINDER_DEFAULT_AMBIT``
========================

:Default: ``'default'``

Slug of the ambit used when none is given explicitly — in particular by
:class:`~finder.models.fields.FinderFileField` and
:class:`~finder.models.fields.FinderFolderField` when they are declared without an ``ambit``
argument. It must match the slug of an existing :class:`~finder.models.ambit.AmbitModel`;
nothing creates one for you.


``FINDER_PAYLOAD_VALIDATORS``
=============================

:Default: ``[]``

Validators run against an uploaded payload, as a list of ``(mime_type, validator)`` 2-tuples.
The same MIME type may appear more than once, in which case every validator registered for it
runs.

A validator is a callable taking ``(file_name, file, owner, mime_type)`` that raises to
reject the file. The configured value may be a dotted path, a callable, or a class — a class
is instantiated once and its instance called.

.. code-block:: python

    FINDER_PAYLOAD_VALIDATORS = [
        ('image/svg+xml', 'finder.contrib.image.svg.validators.svg_validator'),
    ]

See :doc:`../how-to/validate-uploads`.

.. todo::

   The ``feat/validator-compat`` branch reshapes this setting and adds
   ``FINDER_DEFAULT_PAYLOAD_VALIDATORS`` and ``FINDER_REMOVE_PAYLOAD_VALIDATORS``. Update this
   page when it lands.


Django settings django-finder relies on
=======================================

``STORAGES``
    Must contain one entry per storage named by an ambit — see
    :doc:`../how-to/configure-storages`.

``LANGUAGES`` and ``LANGUAGE_CODE``
    Used by :class:`~finder.contrib.image.models.ImageFileModel` to offer one alternative
    text per configured language.

.. todo::

   Audit ``finder/`` for any other Django setting it reads through the
   :mod:`finder.settings` proxy, and list them here.
