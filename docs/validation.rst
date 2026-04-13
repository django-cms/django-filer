.. _validation:

Validation of uploaded files
============================

.. versionadded:: 3.0

While you can control who uploads files using permissions this still leaves
a security vulnerability: A user might knowingly or unknowingly upload a
corrupted file which could cause harm to other staff users or
even visitors of the website.

To this end django-filer implements a basic file validation
framework. By default, it will reject any HTML files for upload and
sanitize uploaded SVG files, stripping any scripts, event handlers or
other non-graphic content.

.. warning::

    File validation is done at upload time. It does not affect already
    uploaded files.

Mime type white list
--------------------

The first thing you can do to set up a security policy is to only allow
white-listed MIME types for upload.

The setting ``FILER_MIME_TYPE_WHITELIST`` (default: ``[]``)  is a list of
strings django-filer will consider for upload, e.g.::

    FILER_MIME_TYPE_WHITELIST = [
        "text/plain",  # Exact MIME type match
        "image/*",  # All types of "image"
    ]

If ``FILER_MIME_TYPE_WHITELIST`` is empty, all MIME types will be accepted
(default behaviour).

.. note::

    django-filer determines the MIME type of a file by its extension.
    It does **not** check if the file format is aligned with its extension.
    Restricting MIME types therefore effectively blocks certain extensions.
    It does not prevent a user from uploading an .exe file disguised as
    an image file, say .jpeg.


Validation hooks
----------------

Uploaded files are validated by their MIME type. The two bundled validators
reject any ``text/html`` file and sanitize files with the MIME type
``image/svg+xml``. Both HTML and SVG files are dangerous since they are
executed by a browser without any warnings.

Validation hooks do not restrict the upload of other executable files
(like ``*.exe`` or shell scripts). **Those are not automatically executed
by the browser but still present a point of attack, if a user saves them
to disk and executes them locally.**

You can release validation restrictions by setting
``FILER_REMOVE_FILE_VALIDATORS`` to a list of MIME types to be removed from
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
(MIME type `text/html``).

The second built-in validator, ``filer.validation.sanitize_svg``, parses
uploaded SVG files and rewrites them with any scripts, event handlers and
other non-graphic content removed. It is powered by
`py-svg-hush <https://pypi.org/project/py-svg-hush/>`_, a Python binding
for the Rust `svg-hush <https://github.com/kornelski/svg-hush>`_ library.
Because the sanitizer runs in native code it is fast enough to apply to
every upload by default.

.. note::

    The sanitized SVG is not byte-identical to the uploaded file: comments,
    scripts, event handlers, external references and other potentially
    dangerous constructs are stripped. The visual appearance of the
    graphic is preserved.

If ``py-svg-hush`` cannot parse the file (for example because it is not a
valid SVG), the upload is rejected with a ``FileValidationError``.

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
        "application/octet-stream",
    ]

No HTML upload, sanitized SVG upload, no binary or unknown file upload
......................................................................

This is the default setting. HTML uploads are rejected, SVG uploads are
sanitized by ``filer.validation.sanitize_svg`` (see above), and binary or
unknown files are rejected.

.. note::

    If you identify an attack vector that survives ``sanitize_svg`` please
    contact the maintainer only through
    `security@django-cms.org <mailto:security@django-cms.org>`_.



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

(Still not binary or unknown file upload)

Strict SVG rejection (legacy behaviour)
.......................................

Previous versions of django-filer shipped with a ``validate_svg`` validator
that rejected any SVG file containing ``<script``, ``javascript:`` or an
event handler attribute. It is still available if you prefer rejecting
suspicious SVGs over rewriting them:

.. code-block:: python

    FILER_REMOVE_FILE_VALIDATORS = ["image/svg+xml"]

    FILER_ADD_FILE_VALIDATORS = {
        "image/svg+xml": ["filer.validation.validate_svg"],
    }

This approach is prone to false positives, since those byte sequences can
legitimately appear inside SVG text content. ``sanitize_svg`` (the
default) is usually the better choice.

Block other MIME types
----------------------

To block other MIME types add an entry for that MIME type to
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

If you distinguish validation by the MIME type, remember to register the
validator function for all relevant MIME types.


.. _check_virus:

Checking uploads for viruses using ClamAV
-----------------------------------------

If you have ClamAV installed and use `django-clamd <https://github.com/vstoykov/django-clamd>`_
you can add a validator that checks for viruses in uploaded files.

.. code-block:: python

    FILER_REMOVE_FILE_VALIDATORS = ["application/octet-stream"]
    FILER_ADD_FILE_VALIDATORS = {
        "application/octet-stream": ["my_validator_app.validators.validate_octet_stream"],
    }


.. code-block:: python

    def validate_octet_stream(file_name: str, file: typing.IO, owner: User, mime_type: str) -> None:
        """Octet streams are binary files without a specific MIME type. They are run through
        a virus check."""
        try:
            from django_clamd.validators import validate_file_infection

            validate_file_infection(file)
        except (ModuleNotFoundError, ImportError):
            raise FileValidationError(
                _('File "{file_name}": Virus check for binary/unknown file not available').format(file_name=file_name)
            )

.. note::

    Virus-checked files still might contain executable code. While the code is not
    executed by the browser, a user might still download the file and execute it
    manually.
