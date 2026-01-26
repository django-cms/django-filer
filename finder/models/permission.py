from functools import lru_cache

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class Privilege(models.TextChoices):
    NONE = '', _("None")
    READ = 'r', _("Read")
    READ_WRITE = 'rw', _("Read & Write")
    WRITE_ONLY = 'w', _("Write (Dropbox)")
    ADMIN = 'admin', _("Administrator")


class AccessControlBase(models.Model):
    privilege = models.CharField(
        max_length=8,
        choices=Privilege.choices,
        default=Privilege.NONE,
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
    everyone = models.BooleanField(
        _("Everyone"),
        default=False,
    )

    class Meta:
        abstract = True

    def __eq__(self, other):
        entry = self.as_dict()
        if isinstance(other, AccessControlBase):
            other = other.as_dict()
        return entry['type']  == other['type'] and entry['principal'] == other['principal']

    def as_dict(self):
        if self.user:
            return {
                'id': self.id,
                'type': 'user',
                'principal': self.user.id,
                'name': str(self.user),
                'privilege': self.privilege,
            }
        if self.group:
            return {
                'id': self.id,
                'type': 'group',
                'principal': self.group.id,
                'name': str(self.group),
                'privilege': self.privilege,
            }
        if self.everyone:
            return {
                'id': self.id,
                'type': 'everyone',
                'principal': None,
                'name': _("Everyone"),
                'privilege': self.privilege,
            }


class AccessControlEntry(AccessControlBase):
    inode = models.UUIDField(db_index=True)

    class Meta:
        verbose_name = _("Access Control Entry")
        verbose_name_plural = _("Access Control Entries")
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(user__isnull=False) & Q(group__isnull=True) & Q(everyone=False)) |
                    (Q(user__isnull=True) & Q(group__isnull=False) & Q(everyone=False)) |
                    (Q(user__isnull=True) & Q(group__isnull=True) & Q(everyone=True))
                ),
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
                condition=Q(everyone=True),
                name='acl_inode_everyone_unique',
            ),
        ]

    def __repr__(self):
        return f'<{self.__class__.__name__}(user={self.user}, inode={self.inode})>'


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
                check=(
                    (Q(user__isnull=False) & Q(group__isnull=True) & Q(everyone=False)) |
                    (Q(user__isnull=True) & Q(group__isnull=False) & Q(everyone=False)) |
                    (Q(user__isnull=True) & Q(group__isnull=True) & Q(everyone=True))
                ),
                name='dacl_single_principal',
            ),
        ]
