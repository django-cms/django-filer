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

    def __new__(cls, *args, **kwargs):
        new_class = super().__new__(cls, *args, **kwargs)
        base_labels = [b._meta.label for b in new_class.mro() if hasattr(b, '_meta')]
        if new_class._meta.abstract is False and 'finder.InodeModel' in base_labels:
            if not new_class.is_folder:
                cls._validate_accept_mime_types(new_class)
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

    @property
    def real_models(self):
        """
        Returns all real (excluding proxy models) that inherit from InodeModel.
        """
        yield self._inode_models['finder.FolderModel']
        for model in self._inode_models.values():
            if not model.is_folder and not model._meta.proxy:
                yield model

    @property
    def file_models(cls):
        """
        Returns all models (including proxy models) that inherit from AbstractFileModel.
        """
        for model in cls._inode_models.values():
            if not model.is_folder:
                yield model


class InodeManagerMixin:
    def filter_inodes(self, **lookup):
        from .folder import FolderModel

        if lookup.pop('is_folder', False):
            return FolderModel.objects.filter(**lookup).iterator()
        inodes = [inode_model.objects.filter(**lookup) for inode_model in InodeModel.real_models]
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
    pattern = re.compile(r"^[\w\s\d]+$")
    if not pattern.match(value):
        msg = "'{filename}' is not a valid filename."
        raise ValidationError(msg.format(filename=value))


class InodeModel(models.Model, metaclass=InodeMetaModel):
    is_folder = False
    folder_component= editor_component = None
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
        # validators=[filename_validator],
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
        Returns a queryset of all ancestor folders starting from the parent folder.
        """
        return self.parent.ancestors

    @cached_property
    def pretty_path(self):
        names = []
        if self.parent:
            names.extend(a.name for a in self.parent.ancestrors)
        names.append(self.name)
        return " / ".join(names)

    def get_sample_url(self):
        """
        Hook to return a URL for a small sample file. Only used in list views.
        """
        return None


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
