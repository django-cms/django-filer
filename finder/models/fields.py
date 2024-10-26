import uuid

from django.db.models.fields import UUIDField
from django.utils.translation import gettext_lazy as _

from finder.forms.fields import FinderFileField as FormFileField
from finder.models.file import FileModel


class FinderFileField(UUIDField):
    description = _("Reference to a file in the finder app.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": FormFileField,
                **kwargs,
            }
        )

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if not isinstance(value, uuid.UUID):
            return value
        return FileModel.objects.get_inode(id=value, is_folder=False)
