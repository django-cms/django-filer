#-*- coding: utf-8 -*-
from django.contrib.sites.models import Site
from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.db import (models, IntegrityError, transaction)
from django.db.models import (query, Q, signals)
from django.dispatch import receiver
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _
from filer.utils.cms_roles import *
from filer.models import mixins
from filer import settings as filer_settings
from datetime import datetime
import mptt
import itertools
import filer


class FoldersChainableQuerySetMixin(object):

    def with_bad_metadata(self):
        return self.filter(has_all_mandatory_data=False)

    def valid_destinations(self, user):
        available_sites = get_sites_for_user(user)
        core_folders = Q(folder_type=Folder.CORE_FOLDER)
        no_site = Q(site__isnull=True)
        shared_folders = ~Q(site__in=available_sites)
        return self.exclude(core_folders | no_site | shared_folders)

    def readonly(self, user):
        core_folders = Q(folder_type=Folder.CORE_FOLDER)
        available_sites = get_sites_for_user(user)
        shared_folders = Q(~Q(site__in=available_sites) &
                           Q(shared__in=available_sites))
        readonly_folders = Q(core_folders | shared_folders)
        return self.filter(readonly_folders)

    def restricted_descendants(self, user):
        sites = get_sites_without_restriction_perm(user)
        if not sites:
            return self.none()
        descendant_filter = None
        for node in self:
            q = Q(**{
                'tree_id': node.tree_id,
                'lft__gt': node.lft - 1,
                'rght__lt': node.rght + 1,
            })
            if descendant_filter is None:
                descendant_filter = q
            else:
                descendant_filter |= q
        if not descendant_filter:
            return self.none()
        # since this method is called to check permissions on descendants it
        #   should only query the alive assets
        restr_q = Q(Q(restricted=True) | Q(
                        Q(all_files__restricted=True) & \
                        Q(all_files__deleted_at__isnull=True)))
        restr_q &= Q(site__in=sites)
        return self.model.objects.filter(
            descendant_filter).filter(restr_q).distinct()

    def unrestricted(self, user):
        sites = get_sites_without_restriction_perm(user)
        if not sites:
            return self
        return self.exclude(restricted=True, site__in=sites)

    def in_trash(self):
        return self.filter(deleted_at__isnull=False)


class EmptyFoldersQS(models.query.EmptyQuerySet,
                     FoldersChainableQuerySetMixin):
    pass


class FolderQueryset(query.QuerySet,
                     FoldersChainableQuerySetMixin):
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


class AliveFolderManager(FolderManager):
    # this is required in order to make sure that other models that are
    #   related to filer folders will get an DoesNotExist exception if the
    #   folder is in trash
    use_for_related_fields = True

    def get_query_set(self):
        return FolderQueryset(self.model, using=self._db).filter(
            deleted_at__isnull=True)


class TrashFolderManager(FolderManager):

    def get_query_set(self):
        return FolderQueryset(self.model, using=self._db).filter(
            deleted_at__isnull=False)


class Folder(mixins.TrashableMixin, mixins.IconsMixin):
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
                              on_delete=models.SET_NULL,
                              null=True, blank=True)

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

    folder_type = models.IntegerField(choices=FOLDER_TYPES.items(),
                                      default=SITE_FOLDER)

    site = models.ForeignKey(Site, null=True, blank=True,
                             on_delete=models.SET_NULL,
                             help_text=_("Select the site which will use "
                                         "this folder."))

    restricted = models.BooleanField(
        _("Restrict Editors and Writers from being able to edit "
          "or delete anything from this folder"), default=False,
        help_text=_('If this box is checked, '
                    'Editors and Writers will still be able to '
                    'view this folder assets, add them to a plugin or smart '
                    'snippet but will not be able to delete or '
                    'modify the current version of the assets.'))

    shared = models.ManyToManyField(Site, null=True, blank=True,
        related_name='shared',
        verbose_name=_("Share folder with sites"),
        help_text=_("All the sites which you share this folder with will "
                    "be able to use this folder on their pages, with all of "
                    "its assets. However, they will not be able to change, "
                    "delete or move it, not even add new assets."))

    objects = AliveFolderManager()
    trash = TrashFolderManager()
    all_objects = FolderManager()
    # required in order for django to know about trashed folders in case of
    #   deleting owners or other related objects
    _base_manager = models.Manager()

    def __init__(self, *args, **kwargs):
        super(Folder, self).__init__(*args, **kwargs)
        self._old_name = self.name
        self._old_parent_id = self.parent_id

    def clean(self):

        if self.name == filer.models.clipboardmodels.Clipboard.folder_name:
            raise ValidationError(
                _(u'%s is reserved for internal use. '
                  'Please choose a different name') % self.name)

        if self.name and "/" in self.name:
            raise ValidationError("Slashes are not allowed in folder names.")

        duplicate_folders_q = Folder.objects.filter(
            parent=self.parent_id,
            name=self.name)
        if self.pk:
            duplicate_folders_q = duplicate_folders_q.exclude(
                pk=self.pk)

        if duplicate_folders_q.exists():
            raise ValidationError(
                'This folder name is already in use. '
                'Please choose a different name.')

        if not self.parent:
            if (self.folder_type == Folder.SITE_FOLDER and
                not self.site):
                raise ValidationError('Folder is a Site folder. '
                                      'Site is required.')
            if (self.folder_type == Folder.CORE_FOLDER and not self.parent and
                self.site):
                raise ValidationError('Folder is a Core folder. '
                                      'Site must be empty.')

    def set_metadata_from_parent(self):
        """
        This will keep the rules:
           * site for site folders can be changed only for the folders
                with no parent(root folders)
           * core folders should not have any site
           * if parent restricted keep restriction from parent
        """
        if self.parent:
            # site folders - make sure it keeps the site from parent
            self.site = self.parent.site
            self.folder_type = self.parent.folder_type
            if self.parent.restricted:
                self.restricted = self.parent.restricted

        if self.is_core():
            self.site = None

        self._update_descendants = self.has_new_metadata_value()

    def has_new_metadata_value(self):
        if not self.pk:
            return True
        metadata_fields = ['restricted', 'site_id', 'folder_type']
        # metadata should be preserved for trashed folder too
        old_metadata = self.__class__.all_objects.\
                 filter(pk=self.pk).values(*metadata_fields).get()
        for field in metadata_fields:
            if getattr(self, field) != old_metadata[field]:
                return True
        return False

    def is_affecting_file_paths(self):
        return (self._old_name != self.name or
                self._old_parent_id != getattr(self.parent, 'id', None))

    def update_descendants_metadata(self):
        """
        Folder type and restriction should be preserved
            to all descendants
        """
        descendants = None
        if self._update_descendants:
            descendants = self.get_descendants()
            descendants.update(
                folder_type=self.folder_type, site=self.site,
                restricted=self.restricted)
            desc_ids = [desc.pk for desc in descendants]
            if self.pk:
                desc_ids.append(self.pk)
            file_mgr = filer.models.filemodels.File.all_objects
            file_mgr.filter(
                folder__in=desc_ids).update(restricted=self.restricted)

        if self.parent:
            parent_shared_sites = self.parent.shared.values_list(
                'id', flat=True)
            instance_shared_sites = self.shared.values_list('id', flat=True)
            if set(instance_shared_sites) != set(parent_shared_sites):
                shared_sites = self.parent.shared.all()
                self.shared = shared_sites
                descendants = descendants or self.get_descendants()
                for desc_folder in descendants:
                    desc_folder.shared = shared_sites

    def save(self, *args, **kwargs):
        if not filer_settings.FOLDER_AFFECTS_URL:
            self.set_metadata_from_parent()
            super(Folder, self).save(*args, **kwargs)
            self.update_descendants_metadata()
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
                self.set_metadata_from_parent()
                super(Folder, self).save(*args, **kwargs)
                self.update_descendants_metadata()
                if self.is_affecting_file_paths():
                    desc_ids = list(self.get_descendants(
                        include_self=True).values_list('id', flat=True))
                    # update location only for alive files
                    file_mgr = filer.models.filemodels.File.objects
                    all_files = file_mgr.filter(folder__in=desc_ids)
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

    def soft_delete(self):
        deletion_time = datetime.now()
        desc_ids = list(self.get_descendants(
            include_self=True).values_list('id', flat=True))
        # soft delete all alive files
        file_mgr = filer.models.filemodels.File.objects
        files_qs = file_mgr.filter(folder__in=desc_ids)
        for filer_file in files_qs:
            filer_file.soft_delete(deletion_time=deletion_time)
        # soft delete all alive folders
        Folder.objects.filter(
            id__in=desc_ids).update(deleted_at=deletion_time)
        self.deleted_at = deletion_time

    def hard_delete(self):
        # This would happen automatically by ways of the delete
        #       cascade, but then the individual .delete() methods
        #       won't be called and the files won't be deleted
        #       from the filesystem.
        desc_ids = list(self.get_descendants(
            include_self=True).values_list('id', flat=True))
        file_mgr = filer.models.filemodels.File.all_objects
        for file_obj in file_mgr.filter(folder__in=desc_ids):
            file_obj.hard_delete()
        super(Folder, self).delete()

    def delete(self, *args, **kwargs):
        super(Folder, self).delete_restorable(*args, **kwargs)
    delete.alters_data = True

    @property
    def trashed_file_count(self):
        file_mgr = filer.models.filemodels.File.trash
        return file_mgr.filter(folder_id=self.id).count()

    @property
    def trashed_children_count(self):
        return Folder.trash.filter(parent_id=self.id).count()

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
    def trashed_files(self):
        trash_file_mgr = filer.models.filemodels.File.trash
        if not self.pk:
            return trash_file_mgr.get_empty_query_set()
        return trash_file_mgr.filter(folder=self).order_by(
            'title', 'name', 'original_filename')

    @property
    def files(self):
        return filer.models.File.objects.filter(folder=self)

    def entries_with_names(self, names):
        """Returns an iterator yielding the files and folders that are direct
        children of this folder and have their names in the given list of names.
        """
        q = Q(name__in=names)
        q |= Q(original_filename__in=names) & (Q(name__isnull=True) | Q(name=''))
        files_with_names = filer.models.File.objects.filter(
            folder=self).filter(q)
        folders_with_names = Folder.objects.filter(
            parent=self, name__in=names)
        return list(itertools.chain(files_with_names, folders_with_names))

    def pretty_path_entries(self):
        """Returns a list of all the descendant's `alive` entries logical path"""
        subdirs = self.get_descendants(include_self=True).filter(
            deleted_at__isnull=True)
        subdir_files = filer.models.File.objects.filter(folder__in=subdirs)
        file_paths = [x.pretty_logical_path for x in subdir_files]
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
        try:
            if self.parent:
                folder_path.extend(self.parent.get_ancestors(
                    include_self=True).filter(deleted_at__isnull=True))
        except Folder.DoesNotExist:
            pass
        return folder_path

    @property
    def pretty_logical_path(self):
        return u"/%s" % u"/".join([f.name
                                   for f in self.logical_path + [self]])

    @property
    def quoted_logical_path(self):
        return urlquote(self.pretty_logical_path)

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

    @property
    def get_folder_type_display(self):
        if self.shared.exists():
            return 'Shared by site'
        return Folder.FOLDER_TYPES[self.folder_type]

    def is_core(self):
        return self.folder_type == Folder.CORE_FOLDER

    def is_readonly_for_user(self, user):
        return self.is_core() or (
            self.site and not has_role_on_site(user, self.site) and
            self.shared.filter(id__in=get_sites_for_user(user)).exists())

    def is_restricted_for_user(self, user):
        return (self.restricted and (
                    not user.has_perm('filer.can_restrict_operations') or
                    not can_restrict_on_site(user, self.site)))

    def can_change_restricted(self, user):
        """
        Checks if restriction operation is available for this folder.
        """
        if (not user.has_perm('filer.can_restrict_operations') or
                not can_restrict_on_site(user, self.site)):
            return False
        if not self.parent:
            return True
        if self.parent.restricted == self.restricted == True:
            # only parent can be set to True
            return False
        if self.parent.restricted == self.restricted == False:
            return True
        if self.parent.restricted == True and self.restricted == False:
            raise IntegrityError(
                'Re-save folder %s to fix restricted property' % (
                    self.parent.pretty_logical_path))
        return True

    def has_add_permission(self, user):
        # nobody can add subfolders in core folders
        if (self.is_readonly_for_user(user) or
                self.is_restricted_for_user(user)):
            return False
        # only site admins can add subfolders in site folders with no site
        if not self.site and has_admin_role(user):
            return True
        # regular users need to have permissions to add folders and
        #   need to have a role over the site owner of the folder
        if (self.site and user.has_perm('filer.add_folder')
                and has_role_on_site(user, self.site)):
            return True

    def has_change_permission(self, user):
        # nobody can change core folder
        if (self.is_readonly_for_user(user) or
                self.is_restricted_for_user(user)):
            return False
        # only admins can change site folders with no site owner
        if not self.site and has_admin_role(user):
            return True

        if self.site:
            if not self.parent:
                # only site admins can change root site folders
                return has_admin_role_on_site(user, self.site)
            return (user.has_perm('filer.change_folder') and
                    has_role_on_site(user, self.site))
        return False

    def has_delete_permission(self, user):
        if (self.is_readonly_for_user(user) or
                self.is_restricted_for_user(user)):
            return False

        # only super users can delete site folders with no site owner
        if not self.site and user.is_superuser:
            return True

        if self.site:
            if not self.parent:
                # only site admins can delete root site folders
                return has_admin_role_on_site(user, self.site)
            return (user.has_perm('filer.delete_folder') and
                    has_role_on_site(user, self.site))

        return False

    class Meta:
        ordering = ('name',)
        permissions = (("can_use_directory_listing",
                        "Can use directory listing"),
                       ("can_restrict_operations",
                        "Can restrict files or folders"),)
        app_label = 'filer'
        verbose_name = _("Folder")
        verbose_name_plural = _("Folders")

# MPTT registration
try:
    mptt.register(Folder)
except mptt.AlreadyRegistered:
    pass


@receiver(signals.m2m_changed, sender=Folder.shared.through)
def update_shared_sites_for_descendants(instance, **kwargs):
    """
    Makes sure that folders keep all shared sites from their root folder.
    """
    action = kwargs['action']
    if not action.startswith('post_') or instance.parent:
        return

    instance = Folder.all_objects.get(id=instance.id)
    sites = instance.shared.all()
    descendants = instance.get_descendants()
    for desc_folder in descendants:
        desc_folder.shared = sites
