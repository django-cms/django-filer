# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _

import mptt

from .. import settings as filer_settings
from ..utils.compatibility import (
    is_authenticated, python_2_unicode_compatible, reverse,
)
from . import mixins


class FolderManager(models.Manager):
    def with_bad_metadata(self):
        return self.get_query_set().filter(has_all_mandatory_data=False)


class FolderPermissionManager(models.Manager):
    """
    Theses methods are called by introspection from "has_generic_permisison" on
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

            if perm.type == FolderPermission.CHILDREN:
                if p == FolderPermission.ALLOW:
                    allow_list.update(perm.folder.get_descendants().values_list('id', flat=True))
                else:
                    deny_list.update(perm.folder.get_descendants().values_list('id', flat=True))

        # Deny has precedence over allow
        return allow_list - deny_list


@python_2_unicode_compatible
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
    name = models.CharField(_('name'), max_length=255)

    owner = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        verbose_name=_('owner'),
        related_name='filer_owned_folders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

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
        return "/%s" % "/".join([f.name for f in self.logical_path + [self]])

    @property
    def quoted_logical_path(self):
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
        if not is_authenticated(user):
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
        try:
            # Django <=1.6
            model_name = self._meta.module_name
        except AttributeError:
            # Django >1.6
            model_name = self._meta.model_name
        return reverse(
            'admin:{0}_{1}_delete'.format(self._meta.app_label, model_name,),
            args=(self.pk,))

    def __str__(self):
        return "%s" % (self.name,)

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

    class Meta(object):
        # see: https://github.com/django-mptt/django-mptt/pull/577
        index_together = (('tree_id', 'lft'),)
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

    folder = models.ForeignKey(
        Folder,
        verbose_name=('folder'),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    type = models.SmallIntegerField(_('type'), choices=TYPES, default=ALL)
    user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
                             related_name="filer_folder_permissions", on_delete=models.SET_NULL,
                             verbose_name=_("user"), blank=True, null=True)
    group = models.ForeignKey(
        auth_models.Group,
        related_name="filer_folder_permissions",
        verbose_name=_("group"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
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

    class Meta(object):
        verbose_name = _('folder permission')
        verbose_name_plural = _('folder permissions')
        app_label = 'filer'
