from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.db.models.expressions import Exists, F, OuterRef, Q
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _


class Privilege(models.IntegerChoices):
    READ = 1, _("Read")
    WRITE = 2, _("Write (Dropbox)")
    READ_WRITE = 3, _("Read & Write")
    ADMIN = 4, _("Administrator")
    FULL = 7, _("Full Control")


class AccessControlBase(models.Model):
    privilege = models.PositiveSmallIntegerField(
        choices=Privilege.choices,
        default=Privilege.READ,
    )
    user = models.ForeignKey(
        get_user_model(),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    group = models.ForeignKey(
        Group,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True

    @cached_property
    def everyone(self):
        return self.user_id is None and self.group_id is None

    def __eq__(self, other):
        entry = self.as_dict
        if isinstance(other, AccessControlBase):
            other = other.as_dict
        return (
            entry['type'] == other['type']
            and entry['principal'] == other['principal']
            and entry['privilege'] == other['privilege']
        )

    def __hash__(self):
        entry = self.as_dict
        return hash((entry['type'], entry['principal'], entry['privilege']))

    @cached_property
    def principal(self):
        if self.user:
            return {'user': self.user}
        if self.group:
            return {'group': self.group}
        if self.everyone:
            return {'everyone': True}
        raise RuntimeError("AccessControlEntry has no principal")

    @cached_property
    def as_dict(self):
        if self.user:
            return {
                'type': 'user',
                'principal': self.user.id,
                'name': str(self.user),
                'privilege': self.privilege,
            }
        if self.group:
            return {
                'type': 'group',
                'principal': self.group.id,
                'name': str(self.group),
                'privilege': self.privilege,
            }
        if self.everyone:
            return {
                'type': 'everyone',
                'principal': None,
                'name': gettext("Everyone"),
                'privilege': self.privilege,
            }
        raise RuntimeError("AccessControlEntry has no principal")


class AccessControlManager(models.Manager):
    _everyone = Q(user__isnull=True, group__isnull=True)

    def get_privilege_queryset(self, user, privilege):
        group_ids = user.groups.values_list('id', flat=True)
        return self.get_queryset().annotate(privilege_mask=F('privilege').bitand(privilege)).filter(
            Q(privilege_mask__gt=0)
            & (self._everyone | Q(user_id=user.id) | Q(group_id__in=group_ids))
        )

    def privilege_subquery_exists(self, user, privilege):
        group_ids = user.groups.values_list('id', flat=True)
        return Exists(self.get_queryset().annotate(privilege_mask=F('privilege').bitand(privilege)).filter(
            Q(privilege_mask__gt=0) & (self._everyone | Q(group_id__in=group_ids) | Q(user_id=user.id)),
            inode=OuterRef('id'),
        ))


class AccessControlEntry(AccessControlBase):
    inode = models.UUIDField(db_index=True)

    class Meta:
        verbose_name = _("Access Control Entry")
        verbose_name_plural = _("Access Control Entries")
        constraints = [
            models.CheckConstraint(
                condition=~Q(user__isnull=False, group__isnull=False),
                name='acl_single_principal',
            ),
            models.UniqueConstraint(
                fields=['inode', 'user'],
                condition=Q(user__isnull=False),
                name='acl_inode_user_unique',
            ),
            models.UniqueConstraint(
                fields=['inode', 'group'],
                condition=Q(group__isnull=False),
                name='acl_inode_group_unique',
            ),
            models.UniqueConstraint(
                fields=['inode'],
                condition=Q(user__isnull=True, group__isnull=True),
                name='acl_inode_everyone_unique',
            ),
            models.CheckConstraint(
                condition=(Q(privilege__in=[Privilege.READ, Privilege.WRITE, Privilege.READ_WRITE, Privilege.FULL])),
                name='acl_valid_privilege',
            ),
        ]

    objects = AccessControlManager()

    def __repr__(self):
        principal = '{0}={1}'.format(*next(iter(self.principal.items())))
        privilege = f'privilege={self.get_privilege_display().replace(" & ", "&")}'
        return f'<{self.__class__.__name__}(inode={self.inode}, {principal}, {privilege})>'


class DefaultAccessControlEntry(AccessControlBase):
    folder = models.ForeignKey(
        'finder.FolderModel',
        on_delete=models.CASCADE,
        related_name='default_access_control_list',
    )

    class Meta:
        verbose_name = _("Default Access Control Entry")
        verbose_name_plural = _("Default Access Control Entries")
        constraints = [
            models.CheckConstraint(
                condition=~Q(user__isnull=False, group__isnull=False),
                name='dacl_single_principal',
            ),
            models.CheckConstraint(
                condition=(Q(privilege__in=[Privilege.READ, Privilege.WRITE, Privilege.READ_WRITE, Privilege.FULL])),
                name='dacl_valid_privilege',
            ),
        ]

    def __repr__(self):
        principal = '{0}={1}'.format(*next(iter(self.principal.items())))
        privilege = f'privilege={self.get_privilege_display().replace(" & ", "&")}'
        return f'<{self.__class__.__name__}(folder={self.folder}, {principal}, {privilege})>'
