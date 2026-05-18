from django.conf import settings


# Default ambit slug to use when no ambit is specified
# This should match the slug of an AmbitModel instance in your database
FINDER_DEFAULT_AMBIT = getattr(settings, 'FINDER_DEFAULT_AMBIT', 'default')


# A list of 2-tuples, where the first entry is the MIME-type of a file to be validated
# and the second entry is a dotted path to a callable that takes a file-like object and raises a ValidationError if the
# file is invalid. This can be used to add custom validation for files uploaded to django-finder.
# It is possible to register multiple validators for the same MIME-type, in which case all validators will be run for
# files of that type.
FINDER_PAYLOAD_VALIDATORS = []
