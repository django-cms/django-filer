#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from filer.fields.permission_set import PermissionSetField
from filer.models import mixins
from filer import settings as filer_settings
from filer.utils.compatibility import python_2_unicode_compatible

import mptt


class FolderManager(models.Manager):
    def with_bad_metadata(self):
        return self.get_query_set().filter(has_all_mandatory_data=False)


class FolderPermissionManager(models.Manager):
    """
    Theses methods are called by introspection from "has_generic_permisison" on
    the folder model.
    """
    # TODO: remove once we have written a migration
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

            if perm.type == FolderPermission.CHILDREN:
                if p == FolderPermission.ALLOW:
                    allow_list.update(perm.folder.get_descendants().values_list('id', flat=True))
                else:
                    deny_list.update(perm.folder.get_descendants().values_list('id', flat=True))

        # Deny has precedence over allow
        return allow_list - deny_list


@python_2_unicode_compatible
class Folder(models.Model, mixins.IconsMixin, mixins.PermissionRefreshMixin):
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

    parent = models.ForeignKey('self', verbose_name=_('parent'), null=True, blank=True,
                               related_name='children')
    name = models.CharField(_('name'), max_length=255)

    owner = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), verbose_name=('owner'),
                              related_name='filer_owned_folders',
                              null=True, blank=True)

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'),auto_now=True)

    who_can_read_local = PermissionSetField()
    who_can_edit_local = PermissionSetField()

    # de-normalised permission data (for performance)
    who_can_read = PermissionSetField()
    who_can_edit = PermissionSetField()

    objects = FolderManager()

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

    @property
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
        return "/%s" % "/".join([f.name for f in self.logical_path+[self]])

    @property
    def quoted_logical_path(self):
        return urlquote(self.pretty_logical_path)

    def can_edit(self, user):
        return self.who_can_edit.check(user)

    def can_read(self, user):
        return self.who_can_read.check(user)

    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_folder_change',
                                    args=(self.id,))

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing',
                                    args=(self.id,))

    def __str__(self):
        return "%s" % (self.name,)

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

    def save(self, *args, **kwargs):
        # FIXME: use signal
        kwargs.pop('refresh_metadata', None)
        if kwargs.pop('refresh_aggregated_permissions', True):
            self.refresh_aggregated_permissions(save=False, recursively=False)
        return super(Folder, self).save(*args, **kwargs)

    class Meta:
        unique_together = (('parent', 'name'),)
        ordering = ('name',)
        permissions = (("can_use_directory_listing",
                        "Can use directory listing"),)
        app_label = 'filer'
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")

# MPTT registration
try:
    mptt.register(Folder)
except mptt.AlreadyRegistered:
    pass


@python_2_unicode_compatible
class FolderPermission(models.Model):
    # TODO: remove once we have written a migration
    # this is no longer used. But I'm keeping it around until we've written a
    # data migration.
    ALL = 0
    THIS = 1
    CHILDREN = 2

    ALLOW = 1
    DENY = 0

    TYPES = (
        (ALL, _('all items')),
        (THIS, _('this item only')),
        (CHILDREN, _('this item and all children')),
    )

    PERMISIONS = (
        (ALLOW, _('allow')),
        (DENY, _('deny')),
    )

    folder = models.ForeignKey(Folder, verbose_name=('folder'), null=True, blank=True)

    type = models.SmallIntegerField(_('type'), choices=TYPES, default=ALL)
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
                             related_name="filer_folder_permissions",
                             verbose_name=_("user"), blank=True, null=True)
    group = models.ForeignKey(auth_models.Group,
                              related_name="filer_folder_permissions",
                              verbose_name=_("group"), blank=True, null=True)
    everybody = models.BooleanField(_("everybody"), default=False)

    can_edit = models.SmallIntegerField(_("can edit"), choices=PERMISIONS, blank=True, null=True, default=None)
    can_read = models.SmallIntegerField(_("can read"), choices=PERMISIONS, blank=True, null=True, default=None)
    can_add_children = models.SmallIntegerField(_("can add children"), choices=PERMISIONS, blank=True, null=True, default=None)

    objects = FolderPermissionManager()

    def __str__(self):
        if self.folder:
            name = '%s' % self.folder
        else:
            name = 'All Folders'

        ug = []
        if self.everybody:
            ug.append('Everybody')
        else:
            if self.group:
                ug.append("Group: %s" % self.group)
            if self.user:
                ug.append("User: %s" % self.user)
        usergroup = " ".join(ug)
        perms = []
        for s in ['can_edit', 'can_read', 'can_add_children']:
            perm = getattr(self, s)
            if perm == self.ALLOW:
                perms.append(s)
            elif perm == self.DENY:
                perms.append('!%s' % s)
        perms = ', '.join(perms)
        return "Folder: '%s'->%s [%s] [%s]" % (
                        name, self.get_type_display(),
                        perms, usergroup)

    def clean(self):
        if self.type == self.ALL and self.folder:
            raise ValidationError('Folder cannot be selected with type "all items".')
        if self.type != self.ALL and not self.folder:
            raise ValidationError('Folder has to be selected when type is not "all items".')
        if self.everybody and (self.user or self.group):
            raise ValidationError('User or group cannot be selected together with "everybody".')
        if not self.user and not self.group and not self.everybody:
            raise ValidationError('At least one of user, group, or "everybody" has to be selected.')

    class Meta:
        verbose_name = _('folder permission')
        verbose_name_plural = _('folder permissions')
        app_label = 'filer'
