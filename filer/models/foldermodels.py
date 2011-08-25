#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from filer.models import mixins
from filer import settings as filer_settings

import mptt


class FolderManager(models.Manager):
    def with_bad_metadata(self):
        return self.get_query_set().filter(has_all_mandatory_data=False)


class FolderPermissionManager(models.Manager):
    """
    Theses methods are called by introspection from "has_generic_permisison" on
    the folder model.
    """
    pass


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

    parent = models.ForeignKey('self', null=True, blank=True,
                               related_name='children')
    name = models.CharField(max_length=255)

    owner = models.ForeignKey(auth_models.User,
                              related_name='filer_owned_folders',
                              null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

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

    def can_view(self, user):
        return self.can(user, 'view')

    def can_add(self, user):
        return self.can(user, 'add')

    def can_change(self, user):
        return self.can(user, 'change')

    def can_delete(self, user):
        return self.can(user, 'delete')

    def can(self, user, permission):
        """
        return True or False if the user has the permission
        """
        if isinstance(permission, basestring):
            permission = PERMISSIONS[permission][0]
        return Permission.objects.children_with_permission_by_user(user, self.pk, permission)

    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_folder_change',
                                    args=(self.id,))

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing',
                                    args=(self.id,))

    def __unicode__(self):
        return u"%s" % (self.name,)

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

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


class OldFolderPermission(models.Model):
    ALL = 0
    THIS = 1
    CHILDREN = 2

    TYPES = (
        (ALL, _('all items')),
        (THIS, _('this item only')),
        (CHILDREN, _('this item and all children')),
    )
    folder = models.ForeignKey(Folder, null=True, blank=True)

    type = models.SmallIntegerField(_('type'), choices=TYPES, default=0)
    user = models.ForeignKey(auth_models.User,
                             related_name="filer_folder_permissions",
                             verbose_name=_("user"), blank=True, null=True)
    group = models.ForeignKey(auth_models.Group,
                              related_name="filer_folder_permissions",
                              verbose_name=_("group"), blank=True, null=True)
    everybody = models.BooleanField(_("everybody"), default=False)

    can_edit = models.BooleanField(_("can edit"), default=True)
    can_read = models.BooleanField(_("can read"), default=True)
    can_add_children = models.BooleanField(_("can add children"), default=True)

    objects = FolderPermissionManager()

    def __unicode__(self):
        if self.folder:
            name = u'%s' % self.folder
        else:
            name = u'All Folders'

        ug = []
        if self.everybody:
            user = 'Everybody'
        else:
            if self.group:
                ug.append(u"Group: %s" % self.group)
            if self.user:
                ug.append(u"User: %s" % self.user)
        usergroup = " ".join(ug)
        perms = []
        for s in ['can_edit', 'can_read', 'can_add_children']:
            if getattr(self, s):
                perms.append(s)
        perms = ', '.join(perms)
        return u"Folder: '%s'->%s [%s] [%s]" % (
                        name, unicode(self.TYPES[self.type][1]),
                        perms, usergroup)

    class Meta:
        verbose_name = _('folder permission')
        verbose_name_plural = _('folder permissions')
        app_label = 'filer'
