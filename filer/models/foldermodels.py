#-*- coding: utf-8 -*-
import itertools
from django.contrib.sites.models import Site
from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import query
from django.db import transaction
from django.db.models import Q
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _

import filer.models.clipboardmodels
from filer.models import mixins
from filer import settings as filer_settings

import mptt


class FoldersChainableQuerySet(object):

    def with_bad_metadata(self):
        return self.filter(has_all_mandatory_data=False)

    def restricted(self, user=None):
        restricted_folder = Q(folder_type=Folder.CORE_FOLDER)
        if user and not user.is_superuser:
            restricted_folder |= Q(parent__isnull=True)

        return self.filter(restricted_folder)

class EmptyFoldersQS(models.query.EmptyQuerySet, FoldersChainableQuerySet):
    pass


class FolderQueryset(query.QuerySet, FoldersChainableQuerySet):
    pass


class FolderManager(models.Manager):

    def get_empty_query_set(self):
        return EmptyFoldersQS(self.model, using=self._db)

    def get_query_set(self):
        return FolderQueryset(self.model, using=self._db)

    def __getattr__(self, name):
        if name.startswith('__'):
            return super(FolderManager, self).__getattr__(self, name)
        return getattr(self.get_query_set(), name)


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

    SITE_FOLDER = 0
    CORE_FOLDER = 1

    FOLDER_TYPES = {
        SITE_FOLDER: 'Site Folder',
        CORE_FOLDER: 'Core Folder',
    }

    parent = models.ForeignKey('self', verbose_name=('parent'), null=True,
                               blank=True, related_name='children')
    name = models.CharField(_('name'), max_length=255)

    owner = models.ForeignKey(auth_models.User, verbose_name=('owner'),
                              related_name='filer_owned_folders',
                              null=True, blank=True)

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

    folder_type = models.IntegerField(choices=FOLDER_TYPES.items(),
                                      default=SITE_FOLDER)

    site = models.ForeignKey(Site, null=True, blank=True,
                             help_text=_("Select the site which will use "
                                         "this folder."))

    objects = FolderManager()

    def clean(self):

        if self.name == filer.models.clipboardmodels.Clipboard.folder_name:
            raise ValidationError(
                _(u'%s is reserved for internal use. '
                  'Please choose a different name') % self.name)

        duplicate_folders_q = Folder.objects.filter(
            parent=self.parent_id,
            name=self.name)
        if self.pk:
            duplicate_folders_q = duplicate_folders_q.exclude(
                pk=self.pk)

        if duplicate_folders_q.exists():
            raise ValidationError(
                'File or folder with this name already exists.')

        if not self.parent:
            if (self.folder_type == Folder.SITE_FOLDER and
                not self.site):
                raise ValidationError('Folder is a Site folder. '
                                      'Site is required.')
            if (self.folder_type == Folder.CORE_FOLDER and not self.parent and
                self.site):
                raise ValidationError('Folder is a Core folder. '
                                      'Site must be empty.')

    def set_site_for_folder_type(self):
        """
        This will keep the rules:
           * site for site folders can be changed only for the folders
                with no parent(root folders)
           * core folders should not have any site
        """
        if self.folder_type == Folder.CORE_FOLDER:
            self.site = None
        else:
            # site folders - make sure it keeps the site from parent
            if self.parent:
                self.site = self.parent.site

    def update_descendants_folder_type(self):
        """
        Folder type should be preserved to all descendants
        """
        self.get_descendants().update(
            folder_type=self.folder_type,
            site=self.site)

    def save(self, *args, **kwargs):
        if not filer_settings.FOLDER_AFFECTS_URL:
            self.set_site_for_folder_type()
            super(Folder, self).save(*args, **kwargs)
            self.update_descendants_folder_type()
            return

        with transaction.commit_manually():
            # The manual transaction management here breaks the transaction
            #   management from
            #   django.contrib.admin.options.ModelAdmin.change_view
            storages = []
            old_locations = []
            new_locations = []

            def delete_from_locations(locations, storages):
                for location, storage in zip(locations, storages):
                    storage.delete(location)

            try:
                self.set_site_for_folder_type()
                super(Folder, self).save(*args, **kwargs)
                self.update_descendants_folder_type()
                all_files = []
                for folder in self.get_descendants(include_self=True):
                    all_files += folder.files
                for f in all_files:
                    old_location = f.file.name
                    new_location = f.update_location_on_storage()
                    if old_location != new_location:
                        storages.append(f.file.storage)
                        old_locations.append(old_location)
                        new_locations.append(new_location)
            except:
                try:
                    transaction.rollback()
                finally:
                    delete_from_locations(new_locations, storages)
                raise
            else:
                transaction.commit()
                delete_from_locations(old_locations, storages)

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

    def entries_with_names(self, names):
        """Returns an iterator yielding the files and folders that are direct
        children of this folder and have their names in the given list of names.
        """
        q = Q(name__in=names)
        q |= Q(original_filename__in=names) & (Q(name__isnull=True) | Q(name=''))
        files_with_names = self.all_files.filter(q)
        folders_with_names = self.children.filter(name__in=names)
        return list(itertools.chain(files_with_names, folders_with_names))

    def pretty_path_entries(self):
        """Returns a list of all the descendant's entries logical path"""
        subdirs = self.get_descendants(include_self=True)
        subdir_files = [x.files for x in subdirs]
        super_files = list(itertools.chain.from_iterable(subdir_files))
        file_paths = [x.pretty_logical_path for x in super_files]
        dir_paths = [x.pretty_logical_path for x in subdirs]
        paths = file_paths + dir_paths
        return paths

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
        return u"/%s" % u"/".join([f.name
                                   for f in self.logical_path + [self]])

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
        if not user.is_authenticated():
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

    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_folder_change',
                                    args=(self.id,))

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing',
                                    args=(self.id,))

    def __unicode__(self):
        return u"%s" % (self.name,)

    @property
    def actual_name(self):
        return self.name

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

    def is_restricted(self):
        return self.folder_type == Folder.CORE_FOLDER

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

    folder = models.ForeignKey(Folder, verbose_name=('folder'), null=True, blank=True)

    type = models.SmallIntegerField(_('type'), choices=TYPES, default=ALL)
    user = models.ForeignKey(auth_models.User,
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

    def __unicode__(self):
        if self.folder:
            name = u'%s' % self.folder
        else:
            name = u'All Folders'

        ug = []
        if self.everybody:
            ug.append('Everybody')
        else:
            if self.group:
                ug.append(u"Group: %s" % self.group)
            if self.user:
                ug.append(u"User: %s" % self.user)
        usergroup = " ".join(ug)
        perms = []
        for s in ['can_edit', 'can_read', 'can_add_children']:
            perm = getattr(self, s)
            if perm == self.ALLOW:
                perms.append(s)
            elif perm == self.DENY:
                perms.append('!%s' % s)
        perms = ', '.join(perms)
        return u"Folder: '%s'->%s [%s] [%s]" % (
                        name, unicode(self.TYPES[self.type][1]),
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
