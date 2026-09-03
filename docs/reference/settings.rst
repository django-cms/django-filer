========
Settings
========

All settings are optional and are read from your project's ``settings.py``. django-finder
reads them through :mod:`finder.settings`, which falls back to Django's own settings for any
name it does not define itself.


``FINDER_DEFAULT_AMBIT``
========================

:Default: ``'public'``

Slug of the ambit used when none is given explicitly — in particular by
:class:`~finder.models.fields.FinderFileField` and
:class:`~finder.models.fields.FinderFolderField` when they are declared without an ``ambit``
argument. It is also the name given to the ambit that ``finder.0002_default_ambit`` creates,
so the two agree out of the box.

It must match the slug of an existing :class:`~finder.models.ambit.AmbitModel`. A widget
naming one that does not exist is refused exactly like one the user may not read, so check
the server log rather than the response when a file picker returns ``403``.


``FINDER_CREATE_DEFAULT_AMBIT``
===============================

:Default: ``True``

Whether ``finder.0002_default_ambit`` creates an ambit named by ``FINDER_DEFAULT_AMBIT`` when
the project has none. Set it to ``False`` before migrating for the first time to manage
ambits exclusively with ``manage.py finder`` — see :doc:`../how-to/manage-ambits`.

The setting is read only while that migration is applied, not on every ``migrate``.


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
    Must contain one entry per storage named by an ambit. ``finder_public`` and
    ``finder_public_samples``, which an ambit uses by default, are derived from the
    ``default`` entry when the project declares neither — see
    :doc:`../how-to/configure-storages`.

``MEDIA_ROOT`` and ``MEDIA_URL``
    Where those derived storages put their files, when your ``default`` storage does not
    override them.

``LANGUAGES`` and ``LANGUAGE_CODE``
    Used by :class:`~finder.contrib.image.models.ImageFileModel` to offer one alternative
    text per configured language.

.. todo::

   Audit ``finder/`` for any other Django setting it reads through the
   :mod:`finder.settings` proxy, and list them here.
