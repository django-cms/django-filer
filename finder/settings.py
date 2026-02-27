from django.conf import settings


# Default ambit slug to use when no ambit is specified
# This should match the slug of an AmbitModel instance in your database
FINDER_DEFAULT_AMBIT = getattr(settings, 'FINDER_DEFAULT_AMBIT', 'default')

