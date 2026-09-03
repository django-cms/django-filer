"""
Validation of uploaded payloads.

A validator is a callable taking ``(file_name, file, owner, mime_type)`` that
raises :class:`finder.exceptions.FileValidationError` to reject an upload. It
runs *before* the payload is written to storage and is handed the uploaded file
opened for reading and writing, so it may also rewrite the content in place --
that is how sanitizing validators such as
``finder.contrib.image.svg.validators.sanitize_svg`` work.

This is deliberately the contract django-filer uses for its
``FILER_ADD_FILE_VALIDATORS`` setting, so that validators written for filer --
including third-party ones -- can be used here unchanged.
"""

from functools import lru_cache
from inspect import isclass

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from finder.exceptions import FileValidationError
from finder.settings import FINDER_DEFAULT_PAYLOAD_VALIDATORS


UNKNOWN_MIME_TYPE = 'application/octet-stream'


def deny(file_name, file, owner, mime_type):
    """Reject the file, naming its extension."""
    file_type = file_name.rsplit('.')[-1]
    if file_type == file_name:
        raise FileValidationError(
            _('File “{file_name}”: Upload denied by site security policy.')
            .format(file_name=file_name)
        )
    raise FileValidationError(
        _('File “{file_name}”: {file_type} upload denied by site security policy.')
        .format(file_name=file_name, file_type=file_type.upper())
    )


def deny_html(file_name, file, owner, mime_type):
    """Reject the file. Separate from :func:`deny` for a clearer message."""
    raise FileValidationError(
        _('File “{file_name}”: HTML upload denied by site security policy.')
        .format(file_name=file_name)
    )


@lru_cache(maxsize=None)
def payload_validator(validator):
    """
    Resolve a configured validator to the callable to invoke: a dotted path is
    imported, a class is instantiated, a callable is used as it is.
    """
    if isinstance(validator, str):
        try:
            return payload_validator(import_string(validator))
        except ImportError as exc:
            raise ImproperlyConfigured(f"Could not import payload validator “{validator}”: {exc}")
    if isclass(validator):
        return payload_validator(validator())
    if callable(validator):
        return validator
    raise ImproperlyConfigured(f"Payload validator “{validator!r}” is not callable.")


def get_configured_validators():
    """
    Return the configured validators as a ``{mime_type: [validator, ...]}``
    dict: the built-in defaults, minus what ``FINDER_REMOVE_PAYLOAD_VALIDATORS``
    drops, plus what ``FINDER_PAYLOAD_VALIDATORS`` adds.

    The settings are read on each call so that they can be overridden in tests.
    """
    validators = {
        mime_type: list(configured)
        for mime_type, configured in FINDER_DEFAULT_PAYLOAD_VALIDATORS.items()
    }
    for mime_type in getattr(django_settings, 'FINDER_REMOVE_PAYLOAD_VALIDATORS', []):
        validators.pop(mime_type, None)
    for mime_type, added in _as_mapping(getattr(django_settings, 'FINDER_PAYLOAD_VALIDATORS', {})).items():
        validators.setdefault(mime_type, []).extend(added)
    return validators


def _as_mapping(configured):
    """
    Accept both shapes of ``FINDER_PAYLOAD_VALIDATORS``: a ``{mime_type: [...]}``
    mapping, and the flat list of ``(mime_type, validator)`` 2-tuples finder
    took before the defaults existed.
    """
    if isinstance(configured, dict):
        return {
            mime_type: list(added) if isinstance(added, (list, tuple)) else [added]
            for mime_type, added in configured.items()
        }
    mapping = {}
    for mime_type, validator in configured:
        mapping.setdefault(mime_type, []).append(validator)
    return mapping


def get_validators(mime_type):
    """
    Return the validators to run for ``mime_type``, from the most general match
    to the most specific one, so that a blanket sanitizer runs before a
    validator registered for one exact type.
    """
    configured = get_configured_validators()
    patterns = ['*/*', '{0}/*'.format(mime_type.split('/')[0]), mime_type]
    return [
        payload_validator(validator)
        for pattern in dict.fromkeys(patterns)
        for validator in configured.get(pattern, [])
    ]


def validate_payload(file_name, file, owner, mime_type):
    """
    Run every validator registered for ``mime_type`` against ``file``.

    Each validator is handed the file rewound, and may rewrite it in place. A
    validator signalling rejection with a plain ``ValueError`` is reported as a
    :class:`~finder.exceptions.FileValidationError` like any other.

    :exception django.core.exceptions.ValidationError: If a validator rejects
        the payload.
    """
    mime_type = mime_type or UNKNOWN_MIME_TYPE
    for validator in get_validators(mime_type):
        _rewind(file)
        try:
            validator(file_name, file, owner, mime_type)
        except ValidationError:
            raise
        except ValueError as exc:
            raise FileValidationError(str(exc)) from exc
    _rewind(file)


def _rewind(file):
    try:
        file.seek(0)
    except (AttributeError, OSError, ValueError):  # pragma: no cover
        pass
