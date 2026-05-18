from django.conf import settings as django_settings


# Default ambit slug to use when no ambit is specified
# This should match the slug of an AmbitModel instance in your database
FINDER_DEFAULT_AMBIT = getattr(django_settings, 'FINDER_DEFAULT_AMBIT', 'default')


# A list of 2-tuples, where the first entry is the MIME-type of a file to be validated
# and the second entry is a dotted path to a callable that takes a file-like object and raises a ValueError if the
# file is invalid. This can be used to add custom validation for files uploaded to django-finder.
# It is possible to register multiple validators for the same MIME-type, in which case all validators will be run for
# files of that type.
FINDER_PAYLOAD_VALIDATORS = getattr(django_settings, 'FINDER_PAYLOAD_VALIDATORS', [])


def __getattr__(name):
    """Proxy any unknown attribute to Django's conf.settings."""
    return getattr(django_settings, name)
