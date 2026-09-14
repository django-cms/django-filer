"""
System checks for the finder configuration.

These validate settings only. A check must not touch the database: it runs before
``migrate``, and on databases which may not exist yet — which is also why the default
ambit is created by a data migration rather than reported by a check.
"""

import re

from django.conf import settings as django_settings
from django.core.checks import Error, Warning

from finder.settings import FINDER_DEFAULT_AMBIT


#: `finder.admin.ambit.catch_all_view()` resolves an ambit slug out of the admin URL.
AMBIT_SLUG_RE = re.compile(r'^[-a-zA-Z0-9_]+$')


def check_default_ambit_slug(app_configs, **kwargs):
    if AMBIT_SLUG_RE.match(FINDER_DEFAULT_AMBIT):
        return []
    return [
        Error(
            f"FINDER_DEFAULT_AMBIT “{FINDER_DEFAULT_AMBIT}” is not a valid slug.",
            hint="The admin resolves an ambit by its slug, so it may only contain "
                 "letters, digits, hyphens and underscores.",
            id='finder.E001',
        ),
    ]


def check_ambit_storages(app_configs, **kwargs):
    """
    `finder.apps.FinderConfig.ready()` derives the storages an ambit refers to from the
    `default` one unless the project declares them. That only works for a filesystem
    default, so report the case where it could not.
    """
    from finder.models.ambit import AmbitModel

    missing = [
        alias
        for alias in (
            AmbitModel._meta.get_field('_original_storage').default,
            AmbitModel._meta.get_field('_sample_storage').default,
        )
        if alias not in django_settings.STORAGES
    ]
    if not missing:
        return []
    return [
        Warning(
            "The storages {} are not configured.".format(', '.join(f'\u201c{alias}\u201d' for alias in missing)),
            hint="They could not be derived from the “default” storage either, which only "
                 "works when that is a FileSystemStorage. Declare them in STORAGES, or point "
                 "your ambits at storages you did declare with `manage.py finder edit-ambit`.",
            id='finder.W001',
        ),
    ]
