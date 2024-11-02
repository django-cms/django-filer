import re
import uuid

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models.aggregates import Aggregate
from django.db.models.expressions import F, Value
from django.db.models.fields import BooleanField, CharField
from django.db.models.functions import Lower
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


class GroupConcat(Aggregate):
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s %(expressions)s)'
    # template = '%(function)s(%(distinct)s %(expressions)s%(separator)s)'
    allow_distinct = True

    def __init__(self, expression, distinct=False, ordering=None, separator=',', output_field=None, **extra):
        super().__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            ordering=f' ORDER BY {ordering}' if ordering is not None else '',
            separator=f",'{separator}'",
            output_field=CharField() if output_field is None else output_field,
            **extra
        )


class InodeMetaModel(models.base.ModelBase):
    _inode_models = {}
    _mime_types_mapping = {}

    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        base_labels = [b._meta.label for b in new_class.mro() if hasattr(b, '_meta')]
        if new_class._meta.abstract is False and 'finder.InodeModel' in base_labels:
            if not new_class.is_folder:
                cls._validate_accept_mime_types(new_class)
            if new_class.is_folder:
                assert (
                    all(not model.is_folder for model in cls._inode_models.values()),
                    "Only one model is allowed to be the folder model.",
                )
                # always enforce that the folder model is the first one
                cls._inode_models = dict(**{new_class._meta.label: new_class}, **cls._inode_models)
            else:
                cls._inode_models[new_class._meta.label] = new_class
        return new_class

    def _validate_accept_mime_types(new_class):
        if not hasattr(new_class, 'accept_mime_types'):
            msg = "Attribute accept_mime_types not defined for {}"
            raise ImproperlyConfigured(msg.format(new_class))
        if not isinstance(new_class.accept_mime_types, (list, tuple)):
            msg = "Attribute accept_mime_types must be a list or tuple for {}"
            raise ImproperlyConfigured(msg.format(new_class))
        if not all(isinstance(mime_type, str) for mime_type in new_class.accept_mime_types):
            msg = "Attribute accept_mime_types must be a list of strings for {}"
            raise ImproperlyConfigured(msg.format(new_class))
        for accept_mime_type in new_class.accept_mime_types:
            for other in new_class._inode_models.values():
                if not other.is_folder and accept_mime_type in other.accept_mime_types:
                    msg = "Attribute accept_mime_types {} already defined in {}"
                    raise ImproperlyConfigured(msg.format(accept_mime_type, other))
            new_class._mime_types_mapping[accept_mime_type] = new_class

    def get_models(self, include_proxy=False, include_folder=False):
        """
        Yields all models that inherit from InodeModel.
        If `include_proxy` is True, all proxy models are included.
        If `include_folder` is True, the `FolderModel` is included.
        """
        for model in self._inode_models.values():
            if (not model._meta.proxy or include_proxy) and (not model.is_folder or include_folder):
                yield model


class InodeManagerMixin:
    """
    Mixin class to be added to managers for models ineriting from `Inode`.
    """

    def filter_unified(self, **lookup):
        """
        Returns a unified QuerySet of all folders and files with fields from all involved models inheriting
        from InodeModel. The QuerySet is filtered by the given lookup parameters.
        Entries are represented as dictionaries rather than model instances.
        """
        from .file import FileModel
        from .folder import FolderModel

        def get_queryset(model):
            concrete_fields = list(unified_fields.keys())
            model_field_names = [field.name for field in model._meta.get_fields()]
            annotations = dict(
                is_folder=Value(model.is_folder, output_field=BooleanField()),
                **unified_annotations,
            )
            expressions = {'label_ids':
                Value(None, output_field=CharField()) if model.is_folder
                else GroupConcat('labels__id', distinct=True)
            }
            for name, field in unified_fields.items():
                if name in annotations:
                    concrete_fields.remove(name)
                elif name not in model_field_names:
                    expressions[name] = Value(None, output_field=field)
            queryset = model.objects.values(*concrete_fields, **expressions).annotate(**annotations)
            model_lookup = dict(lookup)
            labels = model_lookup.pop('labels__in', None)
            if labels and 'labels' in model_field_names:
                model_lookup['labels__in'] = labels
            return queryset.filter(**model_lookup)

        unified_fields = {
            field.name: field for field in FolderModel._meta.get_fields()
            if field.concrete and not field.many_to_many and field.name is not 'realm'
        }
        for model in FileModel.get_models():
            for field in model._meta.get_fields():
                if field.concrete and not field.many_to_many:
                    unified_fields.setdefault(field.name, field)
        unified_annotations = {'owner': F('owner__username'), 'name_lower': Lower('name')}
        unified_queryset = get_queryset(FolderModel).union(*[
            get_queryset(model) for model in FileModel.get_models()
        ])
        return unified_queryset

    def get_inode(self, **lookup):
        from .file import FileModel
        from .folder import FolderModel

        if lookup.pop('is_folder', None) is False:
            folder_qs = FolderModel.objects.none()
        elif (folder_qs := FolderModel.objects.filter(**lookup)).exists():
            return folder_qs.get()
        values = folder_qs.values('id', mime_type=Value(None, output_field=models.CharField())).union(*[
            model.objects.values('id', 'mime_type').filter(**lookup) for model in FileModel.get_models()
        ]).get()
        return FileModel.objects.get_model_for(values['mime_type']).objects.get(id=values['id'])

    def get_proxy_object(self, entry):
        """
        Returns a proxy model instance for the given entry. This can be useful for entries returned by
        `filter_unified` since they are dictionaries and not model instances. It hence is an alternative
        to the `get_inode` method but without querying the database.
        Please note that such an object does not dereference related fields and can only be used
        to access their model methods
        """
        from .file import FileModel
        from .folder import FolderModel

        model = FolderModel if entry['is_folder'] else FileModel.objects.get_model_for(entry['mime_type'])
        field_names = [field.name for field in model._meta.get_fields() if not field.is_relation]
        return model(**{field: entry[field] for field in field_names})


class InodeManager(InodeManagerMixin, models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset().select_related('parent')
        return queryset.filter(self.model.mime_types_query())


def filename_validator(value):
    pattern = re.compile(r"^[\w\d &%!/\\()\[\]{}._#~+-]+$")
    if not pattern.match(value):
        msg = "'{filename}' is not a valid filename."
        raise ValidationError(msg.format(filename=value))


class InodeModel(models.Model, metaclass=InodeMetaModel):
    is_folder = False
    data_fields = ['id', 'name', 'parent', 'created_at', 'last_modified_at']

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    parent = models.ForeignKey(
        'finder.FolderModel',
        verbose_name=_("Folder"),
        related_name='+',
        editable=False,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='+',
        on_delete=models.SET_NULL,
        editable=False,
        null=True,
        blank=True,
        verbose_name=_("Owner"),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        db_index=True,
        validators=[filename_validator],
    )
    created_at = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
        editable=False,
    )
    last_modified_at = models.DateTimeField(
        _("Modified at"),
        auto_now=True,
        editable=False,
    )
    meta_data = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    @property
    def ancestors(self):
        """
        Returns an iterable of all ancestor folders starting from the parent folder.
        """
        return self.parent.ancestors

    @cached_property
    def pretty_path(self):
        names = []
        if self.parent:
            names.extend(a.name for a in self.parent.ancestors)
        names.append(self.name)
        return " / ".join(names)

    def serializable_value(self, field_name):
        data = super().serializable_value(field_name)
        if field_name in ['id', 'parent']:
            return str(data)
        if field_name in ['created_at', 'last_modified_at']:
            return data.isoformat()
        if field_name == 'labels':
            return list(self.labels.values('id', 'name', 'color'))
        return data


class DiscardedInode(models.Model):
    inode = models.UUIDField(
        primary_key=True,
    )
    previous_parent = models.ForeignKey(
        'finder.FolderModel',
        related_name='+',
        on_delete=models.CASCADE,
    )
    deleted_at = models.DateTimeField(
        _("Deleted at"),
        auto_now_add=True,
    )
