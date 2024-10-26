import re
import uuid
from itertools import chain

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


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

    def filter_inodes(self, **lookup):
        from .folder import FolderModel

        if is_folder := lookup.pop('is_folder', None):
            return FolderModel.objects.filter(**lookup).iterator()
        concrete_models = InodeModel.get_models(include_folder=is_folder is None)
        inodes = [inode_model.objects.filter(**lookup) for inode_model in concrete_models]
        return chain(*inodes)

    def get_inode(self, **lookup):
        querychain = self.filter_inodes(**lookup)
        try:
            inode = next(querychain)
        except StopIteration:
            raise self.model.DoesNotExist
        if next(querychain, None):
            raise self.model.MultipleObjectsReturned
        return inode


class InodeManager(InodeManagerMixin, models.Manager):
    def get_queryset(self):
        queryset = super().get_queryset().select_related('parent')
        return queryset.filter(self.model.mime_types_query())


def filename_validator(value):
    pattern = re.compile(r"^[\w\d &%!()\[\]{}._#~+-]+$")
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
