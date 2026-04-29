import uuid

from django.db.models.deletion import CASCADE, DO_NOTHING, SET_NULL, SET_DEFAULT
from django.db.models.expressions import F, Value
from django.db.models.fields import CharField, UUIDField
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _

from finder.forms.fields import FinderFileField as FormFileField, FinderFolderField as FormFolderField
from finder.models.file import FileModel
from finder.models.folder import FolderModel


class FinderBaseModelField(UUIDField):
    __slots__ = ('on_delete', 'ambit')  # _references must be a class member
    _references = []  # keep track of all model fields that reference inodes for deletion handling

    def __init__(self, on_delete, **kwargs):
        if not callable(on_delete):
            raise TypeError("on_delete must be callable.")
        self.on_delete = on_delete
        self.ambit = kwargs.pop('ambit', None)
        kwargs.setdefault('db_index', True)
        super().__init__(**kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        self.__class__._references.append((cls, self.attname))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['on_delete'] = self.on_delete
        if self.ambit is not None:
            kwargs['ambit'] = self.ambit
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        return super().formfield(ambit=self.ambit, **kwargs)

    @classmethod
    def get_referenced_inodes(cls, inode_ids):
        querysets = []
        for model, field_name in cls._references:
            field = model._meta.get_field(field_name)
            querysets.append(
                model.objects.filter(**{f'{field_name}__in': inode_ids}).annotate(
                    model_name=Value(model.__name__, output_field=CharField()),
                    field_name=Value(field_name, output_field=CharField()),
                    on_delete=Value(field.on_delete.__name__, output_field=CharField()),
                    inode_id=Cast(F(field_name), output_field=UUIDField())
                ).values('model_name', 'field_name', 'on_delete', 'inode_id')
            )
        return querysets[0].union(*querysets[1:])

    @classmethod
    def update_or_delete_referring_models(cls, inode_ids):
        for model, field_name in cls._references:
            field = model._meta.get_field(field_name)
            if field.on_delete == DO_NOTHING:
                continue
            queryset = model.objects.filter(**{f"{field_name}__in": inode_ids})
            if field.on_delete.__name__ == 'set_on_delete':
                queryset.update(**{field_name: field.on_delete.deconstruct()[1][0]})
            elif field.on_delete == SET_NULL:
                queryset.update(**{field_name: None})
            elif field.on_delete == SET_DEFAULT:
                default = field.get_default()
                queryset.update(**{field_name: default})
            elif field.on_delete == CASCADE:
                queryset.delete()


class FinderFileField(FinderBaseModelField):
    description = _("Reference to a file in the finder app.")

    def __init__(self, on_delete, **kwargs):
        self.accept_mime_types = kwargs.pop('accept_mime_types', None)
        super().__init__(on_delete, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.accept_mime_types is not None:
            kwargs['accept_mime_types'] = self.accept_mime_types
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        return super().formfield(form_class=FormFileField, accept_mime_types=self.accept_mime_types, **kwargs)

    def from_db_value(self, value, expression, connection):
        if not isinstance(value, uuid.UUID):
            return value
        try:
            return FileModel.objects.get_inode(id=value, is_folder=False, mime_types=self.accept_mime_types)
        except FileModel.DoesNotExist:
            return


class FinderFolderField(FinderBaseModelField):
    description = _("Reference to a folder in the finder app.")

    def formfield(self, **kwargs):
        return super().formfield(form_class=FormFolderField)

    def from_db_value(self, value, expression, connection):
        if not isinstance(value, uuid.UUID):
            return value
        try:
            return FolderModel.objects.get(id=value)
        except FolderModel.DoesNotExist:
            return
