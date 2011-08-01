#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext  as _
from filer.fields.file import FilerFileField


WHO_CHOICES = (
    ('everyone', 'Anonymous Users'),
    ('authorized', 'All Authorized (logged in) Users'),
    ('staff', 'Staff Users'),
    ('user', 'A specific User'),
    ('group', 'A specific Group'),
)


SUBJECT_CHOICES = (
    ('root', 'Root'),
    ('folder', 'Folder'),
    ('file', 'File'),
)

DOWNLOAD_PERMISSION = 1
VIEW_PERMISSION = 2
ADD_PERMISSION = 3
CHANGE_PERMISSION = 4
DELETE_PERMISSION = 5

PERMISSIONS = {
    'download': (DOWNLOAD_PERMISSION, 'Download'),  # ('view', 'View'),
    'view': (VIEW_PERMISSION, 'View'),  # ('view', 'View'),
    'add': (ADD_PERMISSION, 'View and Add (subfolders, files)'),  # ('create', 'Create (subfolders, files)'),
    'change': (CHANGE_PERMISSION, 'View, Add and Change'),  # ('change', 'Change'),
    'delete': (DELETE_PERMISSION, 'View, Add, Change and Delete'),  # (delete', 'Delete'),
}
PERMISSION_CHOICES = PERMISSIONS.values()
def permission(permission_name):
    if isinstance(permission_name, basestring):
        return PERMISSIONS[permission_name][0]
    else:
        return permission_name

def filter_by_permission(qs, user, permission):
    groups = user.groups.all()
    if user.is_staff:
        staff_q = Q(permissions__who='staff', permissions__can__gte=permission)
    else:
        staff_q = Q(permissions__who='inexistent')
    qs = qs.filter(
        Q(owner=user) | \
        (
            Q(permissions__user=user, permissions__can__gte=permission) | \
#            Q(permissions__group__in=groups, permissions__can__gte=permission) | \
            Q(permissions__who='everyone', permissions__can__gte=permission) | \
            staff_q
        )
    )
    return qs


class PermissionManager(models.Manager):
    def children_with_permission_by_user(self, user, folder, permission):
        """
        returns a tuple of two querysets
        (folders, files)
        """
        from filer.models import File, Folder
        if isinstance(folder, Folder):
            folder_qs = Folder.objects.filter(parent=folder)
            file_qs = File.objects.filter(folder=folder)
        else:
            folder_qs = Folder.objects.filter(parent_id=folder)
            file_qs = File.objects.filter(folder_id=folder)

        # find out if the permission is given by any parent
        groups = user.groups.all()
        if user.is_staff:
            staff_q = Q(who='staff', can__gte=permission)
        else:
            staff_q = Q(who='inexistent')
        
        if folder:
            parents_qs = Q(subject='root') | Q(folder=folder) | Q(folder__in=folder.get_ancestors())
        else:
            parents_qs = Q(subject='root')
        ancestor_permission_qs = self.filter(
                parents_qs
            ).filter(
                is_inheritable=True
            ).filter(
                Q(user=user, can__gte=permission) | \
                Q(group__in=groups, can__gte=permission) | \
                Q(who='everyone', can__gte=permission) | \
                staff_q
        )
        if ancestor_permission_qs.exists():
            # this means we we inherit the permission from an ancestor folder anyway, so we don't need to care about
            # individual permissions on the sub-items
            return (folder_qs, file_qs, ancestor_permission_qs)

        # we did not inherit the permission and need to check each individual items
        folder_qs = filter_by_permission(folder_qs, user, permission)
        file_qs = filter_by_permission(file_qs, user, permission)
        return (folder_qs, file_qs)
        


class Permission(models.Model):
    who = models.CharField(choices=WHO_CHOICES, max_length=32, default='anonymous')
    user = models.ForeignKey(auth_models.User, null=True, blank=True, related_name='filer_permissions')
    group = models.ForeignKey(auth_models.Group, null=True, blank=True, related_name='filer_permissions')

    subject = models.CharField(choices=SUBJECT_CHOICES, max_length=32, default='root')
    folder = models.ForeignKey('filer.Folder', null=True, blank=True, related_name='permissions')
    file = FilerFileField(null=True, blank=True, related_name='permissions')
    is_inheritable = models.BooleanField(default=True)

    can = models.SmallIntegerField(choices=PERMISSION_CHOICES, default=VIEW_PERMISSION)

    objects = PermissionManager()

    class Meta:
        verbose_name = 'permission'
        verbose_name_plural = 'permissions'
        app_label = 'filer'

    def __unicode__(self):
        if self.who == 'user':
            who = u'user "%s"' % self.user
        elif self.who == 'group':
            who = u'group "%s"' % self.group
        if self.subject == 'file':
            subject = u'file "%s"' % self.file
        elif self.subject == 'folder':
            subject = u'folder "%s"' % self.folder
        return u'%s can %s %s' % (who, self.get_can_display(), subject)

    def clean(self):
        from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
        if self.who == 'user' and not self.user:
            raise ValidationError(_('Please select the user this permission should applied to.'))
        if self.who == 'group' and not self.group:
            raise ValidationError(_('Please select the user this permission should applied to.'))
        if not self.who == 'user':
            self.user = None
        if not self.who == 'group':
            self.group = None
        if self.subject == 'file' and not self.file:
            raise ValidationError(_('Please select the file this permission should applied to.'))
        if self.subject == 'folder' and not self.folder:
            raise ValidationError(_('Please select the folder this permission should applied to.'))
        if not self.subject == 'folder':
            self.folder = None
        if not self.subject == 'file':
            self.file = None