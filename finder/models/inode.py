import re
import uuid
from functools import reduce
from operator import and_, or_

from django import VERSION as DJANGO_VERSION
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError, PermissionDenied, ObjectDoesNotExist
from django.db import connections, models
from django.db.models.aggregates import Aggregate
from django.db.models.expressions import F, Q, Value
from django.db.models.fields import BooleanField, CharField
from django.db.models.functions import Cast, Lower
from django.db.models.query import QuerySet
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _

from finder.models.permission import AccessControlEntry, Privilege

if DJANGO_VERSION < (6, 0):
    try:
        from django.contrib.postgres.aggregates import StringAgg
    except ImportError:  # psycopg2 is not installed
        pass
else:
    from django.db.models.aggregates import StringAgg


class GroupConcat(Aggregate):
    """
    To be used on SQLite, MySQL and MariaDB databases with Django < 6.
    """
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s %(expressions)s)'
    allow_distinct = True

    def __init__(self, expression, distinct=False, ordering=None, output_field=None, **extra):
        super().__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            ordering=f' ORDER BY {ordering}' if ordering is not None else '',
            output_field=CharField() if output_field is None else output_field,
            **extra
        )


NUMERIC_FIELD_TYPES = [
    'IntegerField', 'FloatField', 'DecimalField', 'BigIntegerField', 'SmallIntegerField',
    'PositiveIntegerField', 'PositiveSmallIntegerField', 'PositiveBigIntegerField'
]


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
                assert all(not model.is_folder for model in cls._inode_models.values()), \
                    "Only one model is allowed to be the folder model."
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


class InodeManager(models.Manager):
    """
    Model manager for models ineriting from `Inode`.
    """

    def get_query(self, model, **lookup):
        model_field_names = [field.name for field in model._meta.get_fields()]
        mime_types = lookup.pop('mime_types', None)
        tags = lookup.pop('tags__in', None)
        can_view = lookup.pop('has_read_permission', None)
        can_change = lookup.pop('has_write_permission', None)
        query = reduce(and_, (Q(**{key: value}) for key, value in lookup.items()), Q())

        # query to filter by read/write permissions
        if can_view and can_change:
            query &= Q(can_view=True) & Q(can_change=True)
        elif can_view:
            query &= Q(can_view=True)
        elif can_change:
            query &= Q(can_change=True)

        # query to filter by mime types
        if mime_types and 'mime_type' in model_field_names:
            queries = []
            for mime_type in mime_types:
                main_type, sub_type = mime_type.split('/', 1)
                if main_type == '*':
                    return Q()
                if sub_type == '*':
                    queries.append(Q(mime_type__startswith=f'{main_type}/'))
                else:
                    queries.append(Q(mime_type=mime_type))
            query &= reduce(or_, queries, Q())

        # query to filter by tags
        if tags and 'tags' in model_field_names:
            query &= Q(tags__in=tags)

        return query

    def get_queryset(self):
        return super().get_queryset().select_related('parent')

    def filter_unified(self, **lookup):
        """
        Returns a unified QuerySet of all folders and files with fields from all involved models
        inheriting from InodeModel. The QuerySet is filtered by the given lookup parameters.
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
            if model.is_folder:
                expressions = {'tag_ids': Value('', output_field=CharField())}
            else:
                connection = connections[model.objects.db]
                if (
                    getattr(connection.features, 'supports_aggregate_distinct_multiple_argument', False)
                    or connection.vendor == 'postgresql'
                ):
                    concatenated = Cast('tags__id', output_field=CharField())
                    expressions = {'tag_ids': StringAgg(concatenated, Value(','), distinct=True)}
                else:
                    # Function STRING_AGG should be preferred over GROUP_CONCAT, but isn't always available or doesn't
                    # support the DISTINCT keyword in SQLite, so we have to use GROUP_CONCAT in that case.
                    expressions = {'tag_ids': GroupConcat('tags__id', distinct=True)}
            if user:
                assert isinstance(user, get_user_model()), "`user` must be an instance of AUTH_USER_MODEL."
                if user.is_superuser:
                    annotations.update(
                        can_view=Value(True, output_field=BooleanField()),
                        can_change=Value(True, output_field=BooleanField()),
                    )
                else:
                    annotations.update(
                        can_view=AccessControlEntry.objects.privilege_subquery_exists(user, Privilege.READ),
                        can_change=AccessControlEntry.objects.privilege_subquery_exists(user, Privilege.WRITE),
                    )
            for name, field in unified_fields.items():
                if name in annotations:
                    concrete_fields.remove(name)
                elif name not in model_field_names:
                    if field.default is models.NOT_PROVIDED:
                        if field.get_internal_type() in NUMERIC_FIELD_TYPES:
                            value = 0
                        elif field.empty_strings_allowed:
                            value = ''
                        else:
                            value = None
                    else:
                        value = field.default
                    expressions[name] = Value(value, output_field=field)
            query = self.get_query(model, **lookup)
            return model.objects.values(*concrete_fields, **expressions).annotate(**annotations).filter(query)

        unified_fields = {
            field.name: field for field in FolderModel._meta.get_fields()
            if field.concrete and not field.many_to_many and field.name != 'ambit'
        }
        for model in FileModel.get_models():
            for field in model._meta.get_fields():
                if field.concrete and not field.many_to_many:
                    unified_fields.setdefault(field.name, field)
        unified_annotations = {'owner': F('owner__username'), 'name_lower': Lower('name')}
        user = lookup.pop('user', None)
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
        try:
            values = folder_qs.values('id', mime_type=Value(None, output_field=models.CharField())).union(*[
                model.objects.values('id', 'mime_type').filter(self.get_query(model, **lookup))
                for model in FileModel.get_models()
            ]).get()
        except FolderModel.DoesNotExist:
            raise self.model.DoesNotExist(f"No inode found matching the given lookup: {lookup}.")
        return FileModel.objects.get_model_for(values['mime_type']).objects.get(id=values['id'])

    @classmethod
    def get_proxy_object(self, entry):
        """
        Returns a proxy model instance for the given entry. This can be useful for entries returned by
        `filter_unified` since they are dictionaries and not model instances. It hence is a faster
        alternative to the `get_inode` method because it does not query the database.
        Note that such an object does not dereference related fields and can only be used
        to access their model members and methods.
        """
        from .file import FileModel
        from .folder import FolderModel

        model = FolderModel if entry['is_folder'] else FileModel.objects.get_model_for(entry['mime_type'])
        field_names = [field.name for field in model._meta.get_fields() if not field.is_relation]
        return model(**{field: entry[field] for field in field_names})


def filename_validator(value):
    pattern = re.compile(r"^[\w\d\s\.&%!_#~+-]+$")
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
    ordering = models.PositiveIntegerField(
        _("Ordering index"),
        default=0,
        editable=False,
        db_index=True,
    )
    meta_data = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        abstract = True
        default_permissions = []

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__}({str(self.id)[:8]}…): name="{self.name}">'

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

    def as_dict(self, ambit):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.replace(microsecond=0, tzinfo=None),
            'last_modified_at': self.last_modified_at.replace(microsecond=0, tzinfo=None),
            'summary': self.summary,
            'meta_data': self.get_meta_data(),
        }

    def serializable_value(self, field_name):
        data = super().serializable_value(field_name)
        if field_name in ['id', 'parent']:
            return str(data)
        if field_name in ['created_at', 'last_modified_at']:
            return data.isoformat()
        if field_name == 'tags':
            return list(self.tags.values('id', 'label', 'color'))
        return data

    def get_meta_data(self):
        return {}

    def has_permission(self, user, privilege):
        assert (privilege & Privilege.FULL) != 0, "Invalid privilege value."
        if user.is_superuser:
            return True
        group_ids = user.groups.values_list('id', flat=True)
        return AccessControlEntry.objects.annotate(privilege_mask=F('privilege').bitand(privilege)).filter(
            Q(privilege_mask__gt=0, inode=self.id)
            & (Q(user__isnull=True, group__isnull=True) | Q(user_id=user.id) | Q(group_id__in=group_ids))
        ).exists()

    def delete(self, *args):
        AccessControlEntry.objects.filter(inode=self.id).delete()
        super().delete(*args)

    def apply_access_control_lists(self, next_acl, user=None, **kwargs):
        if user and not self.has_permission(user, Privilege.ADMIN):
            return

        current_acl_qs = AccessControlEntry.objects.filter(inode=self.id)
        entry_ids, update_entries, create_entries = [], [], []
        if isinstance(next_acl, QuerySet):
            for ace in next_acl:
                try:
                    entry = current_acl_qs.get(user=ace.user, group=ace.group)
                except AccessControlEntry.DoesNotExist:
                    entry = AccessControlEntry(inode=self.id, user=ace.user, group=ace.group, privilege=ace.privilege)
                    create_entries.append(entry)
                else:
                    if entry.privilege != ace.privilege:
                        entry.privilege = ace.privilege
                        update_entries.append(entry)
                    else:
                        entry_ids.append(entry.id)
        else:
            for ace in next_acl:
                if entry := next(filter(
                    lambda ca: ca.as_dict['type'] == ace['type'] and ca.as_dict['principal'] == ace['principal'],
                    current_acl_qs
                ), None):
                    if entry.privilege != ace['privilege']:
                        entry.privilege = ace['privilege']
                        update_entries.append(entry)
                    else:
                        entry_ids.append(entry.id)
                else:
                    create_kwargs = {'inode': self.id, 'privilege': ace['privilege']}
                    if ace['type'] == 'everyone':
                        pass  # user and group are already None
                    elif ace['type'] == 'group':
                        create_kwargs['group_id'] = ace['principal']
                    elif ace['type'] == 'user':
                        create_kwargs['user_id'] = ace['principal']
                    else:
                        raise ValueError(f"Unknown access control type {ace['type']}")
                    create_entries.append(AccessControlEntry(**create_kwargs))

        AccessControlEntry.objects.bulk_update(update_entries, ['privilege'])
        AccessControlEntry.objects.bulk_create(create_entries)
        entry_ids.extend([*(entry.id for entry in update_entries), *(entry.id for entry in create_entries)])
        current_acl_qs.exclude(id__in=entry_ids).delete()


class DiscardedInode(models.Model):
    """
    Store information about inodes that have been moved to the trash folder so that they can be restored again.
    """
    inode = models.UUIDField(
        primary_key=True,
    )
    previous_parent = models.ForeignKey(
        'finder.FolderModel',
        related_name='+',
        on_delete=models.CASCADE,
    )
    trash_folder = models.ForeignKey(
        'finder.FolderModel',
        related_name='+',
        on_delete=models.CASCADE,
    )
    deleted_at = models.DateTimeField(
        _("Deleted at"),
        auto_now_add=True,
    )
