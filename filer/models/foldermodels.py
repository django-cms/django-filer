import warnings
from urllib.parse import quote as urlquote

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

import mptt

from .. import settings as filer_settings
from . import mixins


class FolderPermissionManager(models.Manager):
    """
    These methods are called by introspection from "has_generic_permission" on
    the folder model.
    """
    def get_read_id_list(self, user):
        """
        Give a list of a Folders where the user has read rights or the string
        "All" if the user has all rights.
        """
        return self.__get_id_list(user, "can_read")

    def get_edit_id_list(self, user):
        return self.__get_id_list(user, "can_edit")

    def get_add_children_id_list(self, user):
        return self.__get_id_list(user, "can_add_children")

    def __get_id_list(self, user, attr):
        if user.is_superuser or not filer_settings.FILER_ENABLE_PERMISSIONS:
            return 'All'
        allow_list = set()
        deny_list = set()
        group_ids = user.groups.all().values_list('id', flat=True)
        q = Q(user=user) | Q(group__in=group_ids) | Q(everybody=True)
        perms = self.filter(q).order_by('folder__tree_id', 'folder__level',
                                        'folder__lft')
        for perm in perms:
            p = getattr(perm, attr)

            if p is None:
                # Not allow nor deny, we continue with the next permission
                continue

            if not perm.folder:
                assert perm.type == FolderPermission.ALL

                if p == FolderPermission.ALLOW:
                    allow_list.update(Folder.objects.all().values_list('id', flat=True))
                else:
                    deny_list.update(Folder.objects.all().values_list('id', flat=True))

                continue

            folder_id = perm.folder.id

            if p == FolderPermission.ALLOW:
                allow_list.add(folder_id)
            else:
                deny_list.add(folder_id)

            if perm.type in [FolderPermission.ALL, FolderPermission.CHILDREN]:
                if p == FolderPermission.ALLOW:
                    allow_list.update(perm.folder.get_descendants().values_list('id', flat=True))
                else:
                    deny_list.update(perm.folder.get_descendants().values_list('id', flat=True))

        # Deny has precedence over allow
        return allow_list - deny_list


class Folder(models.Model, mixins.IconsMixin):
    """
    Represents a Folder that things (files) can be put into. Folders are *NOT*
    mirrored in the Filesystem and can have any unicode chars as their name.
    Other models may attach to a folder with a ForeignKey. If the related name
    ends with "_files" they will automatically be listed in the
    folder.files list along with all the other models that link to the folder
    in this way. Make sure the linked models obey the AbstractFile interface
    (Duck Type).
    """
    file_type = 'Folder'
    is_root = False
    can_have_subfolders = True
    _icon = 'plainfolder'

    # explicitly define MPTT fields which would otherwise change
    # and create a migration, depending on django-mptt version
    # (see: https://github.com/django-mptt/django-mptt/pull/578)
    level = models.PositiveIntegerField(editable=False)
    lft = models.PositiveIntegerField(editable=False)
    rght = models.PositiveIntegerField(editable=False)

    parent = models.ForeignKey(
        'self',
        verbose_name=('parent'),
        null=True,
        blank=True,
        related_name='children',
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        _('name'),
        max_length=255,
    )

    owner = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        verbose_name=_('owner'),
        related_name='filer_owned_folders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    uploaded_at = models.DateTimeField(
        _('uploaded at'),
        auto_now_add=True,
    )

    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
    )

    modified_at = models.DateTimeField(
        _('modified at'),
        auto_now=True,
    )

    class Meta:
        # see: https://github.com/django-mptt/django-mptt/pull/577
        index_together = (('tree_id', 'lft'),)
        unique_together = (('parent', 'name'),)
        ordering = ('name',)
        permissions = (("can_use_directory_listing",
                        "Can use directory listing"),)
        app_label = 'filer'
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")

    def __str__(self):
        return self.pretty_logical_path

    def __repr__(self):
        return f'<{self.__class__.__name__}(pk={self.pk}): {self.pretty_logical_path}>'

    @property
    def file_count(self):
        if not hasattr(self, '_file_count_cache'):
            self._file_count_cache = self.files.count()
        return self._file_count_cache

    @property
    def children_count(self):
        if not hasattr(self, '_children_count_cache'):
            self._children_count_cache = self.children.count()
        return self._children_count_cache

    @property
    def item_count(self):
        return self.file_count + self.children_count

    @property
    def files(self):
        return self.all_files.all()

    @cached_property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        folder_path = []
        if self.parent:
            folder_path.extend(self.parent.get_ancestors())
            folder_path.append(self.parent)
        return folder_path

    @property
    def pretty_logical_path(self):
        return format_html('/{}', format_html_join('/', '{0}', ((f.name,) for f in self.logical_path + [self])))

    @property
    def quoted_logical_path(self):
        warnings.warn(
            'Method filer.foldermodels.Folder.quoted_logical_path is deprecated and will be removed',
            DeprecationWarning, stacklevel=2,
        )
        return urlquote(self.pretty_logical_path)

    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')

    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')

    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')

    def has_generic_permission(self, request, permission_type):
        """
        Return true if the current user has permission on this
        folder. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated:
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        else:
            if not hasattr(self, "permission_cache") or\
               permission_type not in self.permission_cache or \
               request.user.pk != self.permission_cache['user'].pk:
                if not hasattr(self, "permission_cache") or request.user.pk != self.permission_cache['user'].pk:
                    self.permission_cache = {
                        'user': request.user,
                    }

                # This calls methods on the manager i.e. get_read_id_list()
                func = getattr(FolderPermission.objects,
                               "get_%s_id_list" % permission_type)
                permission = func(user)
                if permission == "All":
                    self.permission_cache[permission_type] = True
                    self.permission_cache['read'] = True
                    self.permission_cache['edit'] = True
                    self.permission_cache['add_children'] = True
                else:
                    self.permission_cache[permission_type] = self.id in permission
            return self.permission_cache[permission_type]

    def get_admin_change_url(self):
        return reverse('admin:filer_folder_change', args=(self.id,))

    def get_admin_directory_listing_url_path(self):
        return reverse('admin:filer-directory_listing', args=(self.id,))

    def get_admin_delete_url(self):
        return reverse(
            f'admin:{self._meta.app_label}_{self._meta.model_name}_delete',
            args=(self.pk,)
        )

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False


# MPTT registration
try:
    mptt.register(Folder)
except mptt.AlreadyRegistered:
    pass


class FolderPermission(models.Model):
    ALL = 0
    THIS = 1
    CHILDREN = 2

    ALLOW = 1
    DENY = 0

    TYPES = [
        (ALL, _("all items")),
        (THIS, _("this item only")),
        (CHILDREN, _("this item and all children")),
    ]

    PERMISIONS = [
        (None, _("inherit")),
        (ALLOW, _("allow")),
        (DENY, _("deny")),
    ]

    folder = models.ForeignKey(
        Folder,
        verbose_name=("folder"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    type = models.SmallIntegerField(
        _("type"),
        choices=TYPES,
        default=ALL,
    )

    user = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        related_name="filer_folder_permissions",
        on_delete=models.SET_NULL,
        verbose_name=_("user"),
        blank=True,
        null=True,
    )

    group = models.ForeignKey(
        auth_models.Group,
        related_name="filer_folder_permissions",
        verbose_name=_("group"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    everybody = models.BooleanField(
        _("everybody"),
        default=False,
    )

    can_read = models.SmallIntegerField(
        _("can read"),
        choices=PERMISIONS,
        blank=True,
        null=True,
        default=None,
    )

    can_edit = models.SmallIntegerField(
        _("can edit"),
        choices=PERMISIONS,
        blank=True,
        null=True,
        default=None,
    )

    can_add_children = models.SmallIntegerField(
        _("can add children"),
        choices=PERMISIONS,
        blank=True,
        null=True,
        default=None,
    )

    class Meta:
        verbose_name = _('folder permission')
        verbose_name_plural = _('folder permissions')
        app_label = 'filer'

    objects = FolderPermissionManager()

    def __str__(self):
        return self.pretty_logical_path

    def __repr__(self):
        return f'<{self.__class__.__name__}(pk={self.pk}): folder="{self.pretty_logical_path}", ' \
               'who="{self.who}", what="{self.what}">'

    def clean(self):
        if self.type == self.ALL and self.folder:
            raise ValidationError('Folder cannot be selected with type "all items".')
        if self.type != self.ALL and not self.folder:
            raise ValidationError('Folder has to be selected when type is not "all items".')
        if self.everybody and (self.user or self.group):
            raise ValidationError('User or group cannot be selected together with "everybody".')
        if not self.user and not self.group and not self.everybody:
            raise ValidationError('At least one of user, group, or "everybody" has to be selected.')

    @cached_property
    def pretty_logical_path(self):
        if self.folder:
            return self.folder.pretty_logical_path
        return _("All Folders")

    pretty_logical_path.short_description = _("Logical Path")

    @cached_property
    def who(self):
        """
        Returns a human readable string of *who* can interact with a given folder
        """
        parts = []
        if self.user:
            parts.append(_("User: {user}").format(user=self.user))
        if self.group:
            parts.append(_("Group: {group}").format(group=self.group))
        if self.everybody:
            parts.append(_("Everybody"))
        if parts:
            return format_html_join("; ", '{}', ((p,) for p in parts))
        return '–'

    who.short_description = _("Who")

    @cached_property
    def what(self):
        """
        Returns a human readable string of *what* a user/group/everybody can do with a given folder
        """
        mapping = {
            'can_edit': _("Edit"),
            'can_read': _("Read"),
            'can_add_children': _("Add children"),
        }
        perms = []
        for key, text in mapping.items():
            perm = getattr(self, key)
            if perm == self.ALLOW:
                perms.append(text)
            elif perm == self.DENY:
                perms.append('\u0336'.join(text) + '\u0336')
        return format_html_join(", ", '{}', ((p,) for p in perms))

    what.short_description = _("What")
