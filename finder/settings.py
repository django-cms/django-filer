from django.conf import settings as django_settings


# Default ambit slug to use when no ambit is specified
# This should match the slug of an AmbitModel instance in your database
# Slug of the ambit a `FinderFileField`/`FinderFolderField` refers to when it declares
# none of its own, and the one `finder.0002_default_ambit` creates. It matches the
# `finder_public`/`finder_public_samples` storages an ambit defaults to.
FINDER_DEFAULT_AMBIT = getattr(django_settings, 'FINDER_DEFAULT_AMBIT', 'public')


# FINDER_CREATE_DEFAULT_AMBIT (default True) makes `migrate` create the ambit named by
# FINDER_DEFAULT_AMBIT when the project has no ambit at all. It is read at call time by
# `finder.management.create_default_ambit`, so that tests can override it.


# The validators run against every uploaded payload unless a project opts out of them.
# They cover the formats a browser executes in the media origin, which is where an uploaded
# file turns into stored XSS against the site's own staff and visitors.
# Note that, unlike django-filer, finder does not deny 'application/octet-stream': its
# FileModel is the documented fallback for everything that matches no other model, and
# browsers report that MIME-type for plenty of harmless files. Projects wanting filer's
# behaviour can add {'application/octet-stream': ['finder.validators.deny']}.
FINDER_DEFAULT_PAYLOAD_VALIDATORS = {
    'text/html': ['finder.validators.deny_html'],
    'application/xhtml+xml': ['finder.validators.deny'],
    'application/xml': ['finder.validators.deny'],
    'text/xml': ['finder.validators.deny'],
    'application/xslt+xml': ['finder.validators.deny'],
    'image/svg+xml': ['finder.contrib.image.svg.validators.sanitize_svg'],
}


# Validators to run in addition to FINDER_DEFAULT_PAYLOAD_VALIDATORS, as a dict mapping a
# MIME-type to a list of validators. A validator is a dotted path to, or a reference to, a
# callable taking (file_name, file, owner, mime_type) that raises
# finder.exceptions.FileValidationError to reject the upload; it may also rewrite the file
# in place. This is the contract django-filer's FILER_ADD_FILE_VALIDATORS uses, so
# validators written for filer work here unchanged.
# The MIME-type may be exact ('image/png'), a subtype wildcard ('image/*') or '*/*'.
# For backwards compatibility a flat list of (mime_type, validator) 2-tuples is accepted too.
#
#     FINDER_PAYLOAD_VALIDATORS = {'image/*': ['myapp.validators.strip_exif']}
#
# MIME-types listed in FINDER_REMOVE_PAYLOAD_VALIDATORS are dropped from the defaults:
#
#     FINDER_REMOVE_PAYLOAD_VALIDATORS = ['image/svg+xml']
#
# See finder.validators for the details.


def __getattr__(name):
    """Proxy any unknown attribute to Django's conf.settings."""
    return getattr(django_settings, name)
