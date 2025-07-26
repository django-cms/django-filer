import uuid

from django.core.exceptions import ValidationError
from django.db.models.fields import UUIDField
from django.utils.translation import gettext_lazy as _

from finder.forms.fields import FinderFileField as FormFileField
from finder.models.file import FileModel


class FinderFileField(UUIDField):
    description = _("Reference to a file in the finder app.")

    def __init__(self, *args, **kwargs):
        self.accept_mime_types = kwargs.pop('accept_mime_types', None)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                'form_class': FormFileField,
                'accept_mime_types': self.accept_mime_types,
                **kwargs,
            }
        )

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if not isinstance(value, uuid.UUID):
            return value
        try:
            return FileModel.objects.get_inode(id=value, is_folder=False, mime_types=self.accept_mime_types)
        except FileModel.DoesNotExist:
            return
