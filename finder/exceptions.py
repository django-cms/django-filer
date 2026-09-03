from django.core.exceptions import ValidationError


class FileValidationError(ValidationError):
    """
    Raised by a payload validator to reject an uploaded file.

    It is a ``django.core.exceptions.ValidationError``, so its ``messages`` are
    written for the uploading user and the views turn it into a 4xx response
    rather than a server error. django-filer's ``FileValidationError`` is the
    same kind of exception, which is what lets validators written for filer be
    used here unchanged.
    """
