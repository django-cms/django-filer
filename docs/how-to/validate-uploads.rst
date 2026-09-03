================
Validate uploads
================

An uploaded file can be checked — and rejected — before it is accepted into the library. This
is how you stop users from uploading content that is dangerous when a browser serves it back
from your media domain.


Register a validator
====================

``FINDER_PAYLOAD_VALIDATORS`` maps a MIME type to the validators that run for it:

.. code-block:: python

    FINDER_PAYLOAD_VALIDATORS = [
        ('image/svg+xml', 'finder.contrib.image.svg.validators.svg_validator'),
        ('image/svg+xml', 'finder.contrib.image.svg.validators.xml_validator'),
    ]


Write your own
==============

A validator is a callable taking four arguments. Raise to reject the file:

.. code-block:: python

    def no_huge_pdfs(file_name, file, owner, mime_type):
        if file.size > 50 * 1024 * 1024:
            raise ValueError(f'{file_name} is larger than 50 MB')

The value in the settings may be a dotted path, a callable, or a class — a class is
instantiated once and its instance called.


Bundled validators
==================

``finder.contrib.image.svg.validators.svg_validator``
    Rejects an SVG that ``py-svg-hush`` considers malicious. Does nothing if ``py-svg-hush``
    is not installed.

``finder.contrib.image.svg.validators.xml_validator``
    Rejects XML that ``defusedxml`` refuses to parse — XXE, entity expansion. Does nothing if
    ``defusedxml`` is not installed.

.. warning::

   ``FINDER_PAYLOAD_VALIDATORS`` is empty by default, so a stock installation validates
   nothing. SVG files in particular are served from your media domain and executed by the
   browser without warning.

.. todo::

   This page describes the ``finder`` branch. The ``feat/validator-compat`` branch changes it
   substantially: validators run before the payload reaches storage and may rewrite it in
   place, rejection is signalled with ``finder.exceptions.FileValidationError``, MIME
   wildcards work, the setting also accepts a ``{mime_type: [...]}`` mapping, and a set of
   default validators is applied unless removed with ``FINDER_REMOVE_PAYLOAD_VALIDATORS``.
   Rewrite this page and :doc:`../reference/settings` when that branch lands.
