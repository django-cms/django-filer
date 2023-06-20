.. _validation:

Validation of uploaded files
============================

.. versionadded:: 3.0

While you can control who uploads files using permissions this still leaves
a security vulnerability: A user might knowingly or unknowingly upload a
corrupted file which could cause harm to other staff users or
even visitors of the website.

To this end django-filer implements a basic file validation
framework. By default, it will reject any HTML files for upload and certain
SVG files that might include JavaScript code.

Validation hooks
----------------

Uploaded files are validated by their mime-type. The two bundled validators
reject and ``text/html`` file and will check for signs of JavaScript code in
files with the mime type ``image/svg+xml``.

You can release validation restrictions by setting
``FILER_REMOVE_FILE_VALIDATORS`` to a list of mime types to be removed from
validation. This is applicable to the two current validators for ``text/html``
and ``image/svg+xml``, but also to any validators that might be added by
default in future versions.

You can add validation restrictions by setting ``FILER_ADD_FILE_VALIDATORS``
to a dictionary of lists. Say, you wanted to add a file validator for HTML
files, you could do this:

.. code-block:: python

    FILER_ADD_FILE_VALIDATORS = {
        "text/html": [  # Mime type
            "my_validator_app.validators.no_javascript",  # Validator run first
            "my_validator_app.validators.no_inline_css",  # Validator run second
        ]
    }

This would imply that two functions in the ``my_validator_app.validators``
module are present that will be called to validate any ``text/html`` file
uploaded:

.. code-block:: python

    from filer.valiation import FileValidationError


    def no_javascript(file_name, file, owner, mime_type):
        """Take the file's name, the file iteslf, the owner user object
        and the mime_type (as string) as a parameter"""
        ...
        if validation_failed:
            # Validation error will be forwarded to the user as admin message
            raise FileValidationError(
                _('File "{}"': Upload rejected since file contains JavaScript code").format(file_name)
            )


Build-in validators
-------------------

The two build-in validators are extremely simple.

.. code-block:: python

    def deny_html(file_name, file, owner, mime_type):
        """Simple validator that denies all files"""
        raise FileValidationError(
            _('File "{}": HTML upload denied by site security policy').format(file_name)
        )

This just rejects any HTML file for upload.

.. code-block:: python

    def validate_svg(file_name, file, owner, mime_type):
        """SVG files must not contain script tags or javascript hrefs.
        This might be too strict but avoids parsing the xml"""
        content = file.read()
        if b"<script" in content or b"javascript:" in content:
            raise FileValidationError(
                _('File "{}": Rejected due to potential cross site scripting vulnerability').format(file_name)
            )


This validator rejects any SVG file that contains the bytes ``<script`` or
``javascript:``. This probably is a too strict criteria, since those bytes
might be part of a legitimate say string. The above code is a simplification
the actual code also checks for occurences of event attribute like
``onclick="..."``.

.. note::

    If you have legitimate SVG files that contain either ``<script`` or
    ``javascript:`` as byte sequences try escaping the ``<`` and ``:``.

Clearly, the validator can be improved by parsing the SVG's xml code, but
this could be error-prone and we decided to go with the potentially too strict
but simpler method.

Common validator settings
=========================

Here are common examples for settings (in ``settings.py``) on file upload
validation.

Allow upload of any file
------------------------

.. code-block:: python

    FILER_REMOVE_FILE_VALIDATORS = [
        "text/html",
        "image/svg+xml",
    ]

No HTML upload and restricted SVG upload
----------------------------------------

This is the default setting.

No HTML and no SVG upload
-------------------------

.. code-block:: python

    FILER_ADD_FILE_VALIDATORS = {
        "text/html": ["filer.validators.deny_html"],
        "image/svg+xml": ["filer.validators.deny_svg"],
    }
