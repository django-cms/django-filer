import uuid

from django.db.models.fields import UUIDField
from django.utils.translation import gettext_lazy as _

from finder.forms.fields import FinderFileField as FormFileField, FinderFolderField as FormFolderField
from finder.models.file import FileModel
from finder.models.folder import FolderModel


class FinderFileField(UUIDField):
    description = _("Reference to a file in the finder app.")

    def __init__(self, *args, **kwargs):
        self.accept_mime_types = kwargs.pop('accept_mime_types', None)
        self.realm = kwargs.pop('realm', None)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                'form_class': FormFileField,
                'accept_mime_types': self.accept_mime_types,
                'realm': self.realm,
                **kwargs,
            }
        )

    def from_db_value(self, value, expression, connection):
        if not isinstance(value, uuid.UUID):
            return value
        try:
            return FileModel.objects.get_inode(id=value, is_folder=False, mime_types=self.accept_mime_types)
        except FileModel.DoesNotExist:
            return


class FinderFolderField(UUIDField):
    description = _("Reference to a folder in the finder app.")

    def __init__(self, *args, **kwargs):
        self.realm = kwargs.pop('realm', None)
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                'form_class': FormFolderField,
                'realm': self.realm,
                **kwargs,
            }
        )

    def from_db_value(self, value, expression, connection):
        if not isinstance(value, uuid.UUID):
            return value
        try:
            return FolderModel.objects.get(id=value)
        except FolderModel.DoesNotExist:
            return
