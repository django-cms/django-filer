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

.. warning::

    File validation is done at upload time. It does not affect already
    uploaded files.

Mime type white list
--------------------

The first thing you can do to set up a security policy is to only allow
white-listed mime types for upload.

The setting ``FILER_MIME_TYPE_WHITELIST`` (default: ``[]``)  is a list of
strings django-filer will consider for upload, e.g.::

    FILER_MIME_TYPE_WHITELIST = [
        "text/plain",  # Exact mime type match
        "image/*",  # All types of "image"
    ]

If ``FILER_MIME_TYPE_WHITELIST`` is empty, all mime types will be accepted
(default behaviour).

.. note::

    django-filer determines the mime-type of a file by its extension.
    It does **not** check if the file format is aligned with its extension.
    Restricting mime types therefore effectively blocks certain extensions.
    It does not prevent a user from uploading an .exe file disguised as
    an image file, say .jpeg.


Validation hooks
----------------

Uploaded files are validated by their mime-type. The two bundled validators
reject and ``text/html`` file and will check for signs of JavaScript code in
files with the mime type ``image/svg+xml``. Those files are dangerous since
they are executed by a browser without any warnings.

Validation hooks do not restrict the upload of other executable files
(like ``*.exe`` or shell scripts). Those are not automatically executed
by the browser but still present a point of attack, if a user saves them
to disk and executes them locally.

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
uploaded. See :ref:`own_validator` for more info.

Built-in validators
-------------------

The two built-in validators are extremely simple.

.. code-block:: python

    def deny(file_name, file, owner, mime_type):
        """Simple validator that denies all files"""
        raise FileValidationError(
            _('File "{}": Upload denied by site security policy').format(file_name)
        )

This just rejects any file for upload. By default this happens for HTML files
(mime type `text/html``).

.. code-block:: python

    def validate_svg(file_name, file, owner, mime_type):
        """SVG files must not contain script tags or javascript hrefs.
        This might be too strict but avoids parsing the xml"""
        content = file.read().lower()
        if b"<script" in content or b"javascript:" in content:
            raise FileValidationError(
                _('File "{}": Rejected due to potential cross site scripting vulnerability').format(file_name)
            )


This validator rejects any SVG file that contains the bytes ``<script`` or
``javascript:``. This probably is a too strict criteria, since those bytes
might be part of a legitimate say string. The above code is a simplification
the actual code also checks for occurrences of event attribute like
``onclick="..."``.

.. note::

    If you have legitimate SVG files that contain either ``<script`` or
    ``javascript:`` as byte sequences try escaping the ``<`` and ``:``.

Clearly, the validator can be improved by parsing the SVG's xml code, but
this could be error-prone and we decided to go with the potentially too strict
but simpler method.

Common validator settings
-------------------------

Here are common examples for settings (in ``settings.py``) on file upload
validation.

Allow upload of any file
........................

This setting does not restrict uploads at all. It is only advisable for
setups where all users with upload rights can be fully trusted.

Your site will still be subject to an attack where a trusted user uploads
a malicious file unknowingly.

.. code-block:: python

    FILER_REMOVE_FILE_VALIDATORS = [
        "text/html",
        "image/svg+xml",
    ]

No HTML upload and restricted SVG upload
........................................

This is the default setting. It will deny any SVG file that might contain
Javascript. It is prone to false positives (i.e. files being rejected that
actually are secure).

.. note::

    If you identify false negatives (i.e. files being
    accepted despite containing Javascript) please contact the maintainer only
    through `security@django-cms.org <mailto:security@django-cms.org>`_.



No HTML and no SVG upload
.........................

This is the most secure setting. Both HTML and SVG will be rejected for uploads
since they can contain Javascript and thereby might be used to execute malware
in the user's browser.


.. code-block:: python

    FILER_ADD_FILE_VALIDATORS = {
        "text/html": ["filer.validation.deny_html"],
        "image/svg+xml": ["filer.validation.deny"],
    }

Experimental SVG sanitization
.............................

This experimental feature passes an uploaded SVG image through easy-thumbnail
and is rewritten without non-graphic tags or attributes. Any javascript
within the SVG file will be lost.

The resulting file is not identical to the uploaded file.

.. code-block:: python

    FILER_REMOVE_FILE_VALIDATORS = ["image/svg+xml"]

    FILER_ADD_FILE_VALIDATORS = {
        "image/svg+xml": ["filer.validation.sanitize_svg"],
    }

.. warning::

    This feature is experimental. It is not clear how effective the
    sanitization is in practice. Use it at own risk.

.. note::

    If you identify an attack vector when using ``sanitize_svg`` please
    contact us only through
    `security@django-cms.org <mailto:security@django-cms.org>`_.

Block other mime-types
----------------------

To block other mime types add an entry for that mime type to
``FILER_ADD_FILE_VALIDATORS`` with ``filer.validation.deny``::

    FILER_ADD_FILE_VALIDATORS[mime_type] = ["filer.validation.deny"]


.. _own_validator:

Creating your own file upload validators
----------------------------------------

You can create your own fule upload validators and register them with
``FILER_ADD_FILE_VALIDATORS``.

All you need is a function that validates the upload of a specified
mime type::

    import typing
    from django.contrib.auth import get_user_model
    from filer.validation import FileValidationError


    User = get_user_model()


    def no_javascript(
        file_name: str,
        file: typing.IO,
        owner: User,
        mime_type: str
    ) -> None:
        # You can read the file `file` to test its validity
        # You can also use file_name, owner, or mime_type
        ...
        if invalid:
            raise FileValidationError(
                _('File "{}": Upload rejected since file contains JavaScript code').format(file_name)
            )

The file will be accepted for upload if the validation functions returns
without a ``FileValidationError``.

If the file should be rejected raise a ``FileValidationError``. Its error
message will be forwarded to the user. It is good practice to include the
name of the invalid file since users might be uploading many files at a
time.

The ``owner`` argument is the ``User`` object of the user uploading the file.
You can use it to distinguish validation for certain user groups if needed.

If you distinguish validation by the mime type, remember to register the
validator function for all relevant mime types.
