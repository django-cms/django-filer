#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.db import models
from django.db.models import Q


WHO_CHOICES = (
    ('everyone', 'Anonymous Users and everyone else'),
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


PERMISSION_CHOICES = (
    ('read', 'Read'),
    ('change', 'Change'),
    ('delete', 'Delete'),
    ('add_children', 'Add Children (subfolders, files)'),
)


class PermissionManager(models.Manager):
    def can_read_folders(self, user):
        from filer.models import Folder
        groups = user.groups.all()
        if user.is_staff:
            staff_q = Q(permissions__who='staff', permissions__can='read')
        else:
            staff_q = Q(permissions__who='xxx')
        qs = Folder.objects.filter(
            Q(owner=user) | \
            (
                Q(permissions__user=user, permissions__can='read') | \
                Q(permissions__group__in=groups, permissions__can='read') | \
                Q(permissions__who='everyone', permissions__can='read') | \
                staff_q
            )
        )
        return qs


class Permission(models.Model):
    who = models.CharField(choices=WHO_CHOICES, max_length=32, default='anonymous')
    user = models.ForeignKey(auth_models.User, null=True, blank=True, related_name='filer_permissions')
    group = models.ForeignKey(auth_models.Group, null=True, blank=True, related_name='filer_permissions')

    subject = models.CharField(choices=SUBJECT_CHOICES, max_length=32, default='root')
    folder = models.ForeignKey('filer.Folder', null=True, blank=True, related_name='permissions')
    file = models.ForeignKey('filer.File', null=True, blank=True, related_name='permissions')
    is_inheritable = models.BooleanField(default=True)

    can = models.CharField(choices=PERMISSION_CHOICES, max_length=32, default='read')

    objects = PermissionManager()

    class Meta:
        verbose_name = 'permission'
        verbose_name_plural = 'permissions'
        app_label = 'filer'