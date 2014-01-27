#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext as _
from filer.fields.file import FilerFileField
from filer.models import FolderRoot


WHO_CHOICES = (
    ('everyone', 'Everyone'),  # (Including Anonymous Users)
    # ('authenticated', 'All Authenticated (logged in) Users'),
    # ('staff', 'Staff Users'),
    ('user', 'User'),
    ('group', 'Group'),
)

SUBJECT_CHOICES = (
    ('root', 'Root'),
    ('folder', 'Folder'),
    ('file', 'File'),
)


class PermissionManager(models.Manager):
    pass


class Permission(models.Model):
    """
    holds permission information about the root folder, folders or files.

    Important:
    This model is not actually needed. It is just here because it makes
    building the admin ui easier. The contents of the permissions are
    saved into a TextField on the Folder/File models. Once we build
    a pretty widget to edit those directly, we can get rid of this.
    Still need to find a place to save the Permissions for the virtual "root"
    Folder though.
    """
    # TODO: remove with Permission Model refactor
    ALLOW = 1
    DENY = 0
    PERMISSION_CHOICES = (
        (ALLOW, _('allow')),
        (DENY, _('deny')),
    )
    who = models.CharField(
        choices=WHO_CHOICES, max_length=32, default='group')
    user = models.ForeignKey(
        auth_models.User, null=True, blank=True, related_name='filer_permission_set')
    group = models.ForeignKey(
        auth_models.Group, null=True, blank=True, related_name='filer_permissions_set')

    subject = models.CharField(
        choices=SUBJECT_CHOICES, max_length=32)
    folder = models.ForeignKey(
        'filer.Folder', null=True, blank=True, related_name='permission_set')
    file = FilerFileField(
        null=True, blank=True, related_name='permission_set')

    # can view a folders name. can download a file and view it's metadata
    can_read = models.SmallIntegerField(
        _("can read"), choices=PERMISSION_CHOICES, blank=True, null=True, default=None)
    # can change and delete the folder/file
    can_edit = models.SmallIntegerField(
        _("can edit"), choices=PERMISSION_CHOICES, blank=True, null=True, default=None)

    objects = PermissionManager()

    class Meta:
        verbose_name = 'permission'
        verbose_name_plural = 'permissions'
        app_label = 'filer'

    def __unicode__(self):
        return u'%s can %s %s' % (
            self.get_who_combined_display(), self.get_can_display(), self.get_subject_combined_display())

    def get_subject(self, as_id=False):
        if self.subject == 'file':
            if as_id:
                return self.file_id
            else:
                return self.file
        elif self.subject == 'folder':
            if as_id:
                return self.folder_id
            else:
                return self.folder
        else:
            return FolderRoot()

    def get_who_id(self):
        return self.get_who(as_id=True)

    def get_who(self, as_id=False):
        if self.who == 'user':
            if as_id:
                return self.user_id
            else:
                return self.user
        elif self.who == 'group':
            if as_id:
                return self.group_id
            else:
                return self.group
        elif self.who == 'everyone':
            return None
        else:
            # invalid data. raise?
            pass

    def get_subject_id(self):
        return self.get_subject(as_id=True)

    def get_who_combined_display(self):
        if self.who == 'user':
            who = u'user "%s"' % self.user
        elif self.who == 'group':
            who = u'group "%s"' % self.group
        else:
            who = self.who
        return who

    def get_can_display(self):
        cans = []
        if self.can_read == 1:
            cans.append('read')
        elif self.can_read == 0:
            cans.append('NOT read')
        if self.can_edit == 1:
            cans.append('edit')
        elif self.can_edit == 0:
            cans.append('NOT edit')
        return " and ".join(cans)


    def get_subject_combined_display(self):
        if self.subject == 'file':
            subject = u'file "%s"' % self.file
        elif self.subject == 'folder':
            subject = u'folder "%s"' % self.folder
        else:
            subject = u'"%s"' % self.subject
        return subject

    def clean(self):
        from django.core.exceptions import ValidationError
        # who validation
        if self.who == 'user' and not self.user:
            raise ValidationError(_('Please select the user this permission should applied to.'))
        if self.who == 'group' and not self.group:
            raise ValidationError(_('Please select the group this permission should applied to.'))
        if not self.who == 'user':
            self.user = None
        if not self.who == 'group':
            self.group = None
        # admin inlines on folder/file need this
        if not self.subject and self.folder and not self.file:
            self.subject = 'folder'
        if not self.subject and self.file and not self.folder:
            self.subject = 'file'
        # subject validation
        if self.subject == 'file' and not self.file:
            raise ValidationError(_('Please select the file this permission should applied to.'))
        if self.subject == 'folder' and not self.folder:
            raise ValidationError(_('Please select the folder this permission should applied to.'))
        if not self.subject == 'folder':
            self.folder = None
        if not self.subject == 'file':
            self.file = None
        if self.subject == 'root':
            self.file = None
            self.group = None

    @property
    def can_read_bool(self):
        if self.can_read is None:
            return None
        return bool(self.can_read)

    @property
    def can_edit_bool(self):
        if self.can_edit is None:
            return None
        return bool(self.can_edit)


def handle_permission_change(sender, instance, **kwargs):
    # update the de-normalised field on the subject and update all descendants.
    try:
        subject = instance.get_subject()
    except ObjectDoesNotExist:
        pass
    else:
        if getattr(subject, 'is_root', False):
            # can't actually save anything to a model, since it's the virtual root object.
            # but we should trigger the refresh for all descendants
            for child in subject.children.all():
                child.refresh_aggregated_permissions()
        else:
            subject.refresh_permissions_from_model_workaround()

models.signals.post_save.connect(
    handle_permission_change,
    sender=Permission,
    dispatch_uid='filer.permission.pre_save.handle_permission_change')

models.signals.post_delete.connect(
    handle_permission_change,
    sender=Permission,
    dispatch_uid='filer.permission.post_delete.handle_permission_change')


class PermissionSet(object):
    """
    Holds sets of ids for users and groups for "allow" and "deny".
    PermissionSets can be inherited, where the latest addition takes
    precedence over the existing sets.
    """
    def __init__(self):
        self.all = None  # None means "I don't know". True means allow all, False means deny all
        self.allow_user_ids = set()
        self.deny_user_ids = set()
        self.allow_group_ids = set()
        self.deny_group_ids = set()

    def __repr__(self):
        return '<PermissionSet %s>' % self.to_txt()

    def __unicode__(self):
        return self.to_txt()

    def __cmp__(self, other):
        if other.to_txt() == self.to_txt():
            return 0
        else:
            return 1

    def check(self, user):
        """
        check whether the user is allowed to access based on the rules in this permission set.
        """
        if not isinstance(user, PermissionUser):
            user = PermissionUser(user)
        if user.is_superuser:
            return True
        if self.all:
            return True
        if not user.is_authenticated:
            return False
        deny_by_user = user.id in self.deny_user_ids
        deny_by_group = bool(user.group_ids & self.deny_group_ids)
        if not deny_by_user and user.id in self.allow_user_ids:
            return True
        if not deny_by_user and not deny_by_group and user.group_ids & self.allow_group_ids:
            return True
        return False

    def add_user_id(self, user_id, allow_or_deny):
        if allow_or_deny is True:
            self.allow_user_ids.add(user_id)
        elif allow_or_deny is False:
            self.deny_user_ids.add(user_id)
        elif allow_or_deny is None:
            # can be ignored
            pass
        else:
            # bad value. raise?
            pass

    def add_group_id(self, group_id, allow_or_deny):
        if allow_or_deny is True:
            self.allow_group_ids.add(group_id)
        elif allow_or_deny is False:
            self.deny_group_ids.add(group_id)
        elif allow_or_deny is None:
            # can be ignored
            pass
        else:
            # bad value. raise?
            pass

    def add_permission(self, who, user_or_group_id, allow_or_deny):
        if who == 'user':
            self.add_user_id(user_or_group_id, allow_or_deny)
        elif who == 'group':
            self.add_group_id(user_or_group_id, allow_or_deny)
        elif who == 'everyone':
            self.all = allow_or_deny
        else:
            # invalid subject. raise?
            pass

    def cleanup(self):
        """
        removes conflicting data (deny is more powerful than allow)
        """
        # if they are in deny, they can't be allowed.
        self.allow_user_ids = self.allow_user_ids - self.deny_user_ids
        self.allow_group_ids = self.allow_group_ids - self.deny_group_ids
        return self

    def inherit_from(self, parent):
        """
        parent is the PermissionSet of our parent object.
        We inherit all permissions form it, but our own
        permissions take precedence on exact matches.
        deny is stronger than allow.
        """
        new = parent.clone()
        if self.all is None:
            new.all = parent.all
        else:  # True or False
            new.all = self.all
        # we allow all from our parent plus our own
        new.allow_user_ids |= self.allow_user_ids
        # but any ids the parent might have allowed that we deny must go
        new.allow_user_ids -= self.deny_user_ids
        # we deny all from our parent plus our own
        new.deny_user_ids |= self.deny_user_ids
        # ids we explicitly allow, override any denies from the parent
        new.deny_user_ids -= self.allow_user_ids

        # same for groups
        new.allow_group_ids |= self.allow_group_ids
        new.allow_group_ids -= self.deny_group_ids
        new.deny_group_ids |= self.deny_group_ids
        new.deny_group_ids -= self.allow_group_ids
        new.cleanup()
        return new

    def clone(self):
        """
        Return a new identical PermissionSet object.
        """
        new = PermissionSet()
        new.all = self.all
        new.allow_user_ids = self.allow_user_ids.copy()
        new.deny_user_ids = self.deny_user_ids.copy()
        new.allow_group_ids = self.allow_group_ids.copy()
        new.deny_group_ids = self.deny_group_ids.copy()
        return new

    def to_set(self):
        r = set()
        if self.all is True:
            r.add('+a')
        elif self.all is False:
            r.add('-a')
        for uid in self.allow_user_ids:
            r.add('+u%s' % uid)
        for uid in self.deny_user_ids:
            r.add('-u%s' % uid)
        for gid in self.allow_group_ids:
            r.add('+g%s' % gid)
        for gid in self.deny_group_ids:
            r.add('-g%s' % gid)
        return r

    def to_txt(self):
        return ';%s;' % ';'.join(sorted(self.to_set()))

    @classmethod
    def from_txt(cls, txt):
        txt = txt.strip(';')
        if not txt:
            # it's empty
            return cls()
        items = set(txt.split(';'))
        new = cls()
        for item in items:
            if item == '-a':
                new.all = False
            elif item == '+a':
                new.all = True
            else:
                instruction, value = item[:2], int(item[2:])
                if instruction == '+u':
                    new.allow_user_ids.add(value)
                elif instruction == '-u':
                    new.deny_user_ids.add(value)
                elif instruction == '+g':
                    new.allow_group_ids.add(value)
                elif instruction == '-g':
                    new.deny_group_ids.add(value)
                else:
                    # faulty entry
                    pass
        new.cleanup()
        return new


class PermissionUser(object):
    """
    Provides necessary attributes of a User when using it to check for permissions.
    """
    def __init__(self, user):
        self.id = user.pk
        cache_key = '_filer_permissionuser_hacky_cached_group_ids'
        group_ids = getattr(user, cache_key, None)
        if group_ids is None:
            group_ids = set(user.groups.values_list('pk', flat=True))
            setattr(user, cache_key, group_ids.copy())
        self.group_ids = group_ids
        self.is_superuser = user.is_superuser
        self.is_authenticated = user.is_authenticated()

        # not used yet
        self.is_staff = user.is_staff
        self.is_active = user.is_active


def filter_queryset_by_permissions_for_user(qs, user, perm):
    # FIXME: should behave identical to PermissionSet.check():
    #        * allow user/group should be stronger than deny all
    #        * allow user should be stronger than deny group
    if not isinstance(user, PermissionUser):
        user = PermissionUser(user)
    assert perm in ('read', 'edit')
    if user.is_superuser:
        return qs
    who_can_field_name = 'who_can_%s' % perm
    filters = []
    excludes = []
    # items that allow all are ok
    filters.append(Q(**{'%s__contains' % who_can_field_name: ';+a;'}))
    excludes.append(Q(**{'%s__contains' % who_can_field_name: ';-a;'}))
    if user.is_authenticated:
        # Note: ownership is already handled because we always add the owner_id to allowed
        # filter for this specific user
        filters.append(Q(**{'%s__contains' % who_can_field_name: ';+u%s;' % user.id}))
        excludes.append(Q(**{'%s__contains' % who_can_field_name: ';-u%s;' % user.id}))
        # filter for all groups this user is in
        for gid in user.group_ids:
            filters.append(Q(**{'%s__contains' % who_can_field_name: ';+g%s;' % gid}))
            excludes.append(Q(**{'%s__contains' % who_can_field_name: ';-g%s;' % gid}))
    filter_q = Q()
    for q in filters:
        filter_q |= q
    exclude_q = Q()
    for q in excludes:
        exclude_q |= q
    qs = qs.filter(filter_q).exclude(exclude_q)
    return qs
