#-*- coding: utf-8 -*-
import itertools
from django.contrib.sites.models import Site
from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.db import (models, IntegrityError, transaction)
from django.db.models import (query, Q)
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _
import filer.models.clipboardmodels
from filer.utils.cms_roles import *
from filer.models import mixins
from filer import settings as filer_settings
import mptt


class FoldersChainableQuerySet(object):

    def with_bad_metadata(self):
        return self.filter(has_all_mandatory_data=False)

    def readonly(self):
        readonly_folders = Q(folder_type=Folder.CORE_FOLDER)
        return self.filter(readonly_folders)

    def restricted(self, user):
        sites = get_sites_without_restriction_perm(user)
        if not sites:
            return self.none()
        return self.filter(restricted=True, site__in=sites)

    def unrestricted(self, user):
        sites = get_sites_without_restriction_perm(user)
        if not sites:
            return self
        return self.exclude(restricted=True, site__in=sites)


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

    restricted = models.BooleanField(
        _("Restrict Editors and Writers from being able to edit "
          "or delete anything from this folder"), default=False,
        help_text=_('If this box is checked, '
                    'Editors and Writers will still be able to '
                    'view this folder assets, add them to a plugin or smart '
                    'snippet but will not be able to delete or '
                    'modify the current version of the assets.'))

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
        if self.is_readonly():
            self.site = None
        else:
            # site folders - make sure it keeps the site from parent
            if self.parent:
                self.site = self.parent.site

    def set_restricted_from_parent(self):
        if self.parent and self.parent.restricted:
            self.restricted = self.parent.restricted

    def update_descendants_folder_type(self):
        """
        Folder type should be preserved to all descendants
        """
        self.get_descendants().update(
            folder_type=self.folder_type,
            site=self.site)

    def update_descendants_restricted(self):
        """
        Restricted should be preserved to all descendants
        """
        descendants = self.get_descendants().select_related('all_files')
        descendants.update(restricted=self.restricted)
        self.all_files.update(restricted=self.restricted)
        for desc_folder in descendants:
            desc_folder.all_files.update(restricted=self.restricted)


    def save(self, *args, **kwargs):
        if not filer_settings.FOLDER_AFFECTS_URL:
            self.set_restricted_from_parent()
            self.set_site_for_folder_type()
            super(Folder, self).save(*args, **kwargs)
            self.update_descendants_folder_type()
            self.update_descendants_restricted()
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
                self.set_restricted_from_parent()
                self.set_site_for_folder_type()
                super(Folder, self).save(*args, **kwargs)
                self.update_descendants_folder_type()
                self.update_descendants_restricted()
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

    def is_readonly(self):
        return self.folder_type == Folder.CORE_FOLDER

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
        if self.is_readonly() or self.is_restricted_for_user(user):
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
        if self.is_readonly() or self.is_restricted_for_user(user):
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
        if self.is_readonly() or self.is_restricted_for_user(user):
            return False

        # only admins can delete site folders with no site owner
        if not self.site and has_admin_role(user):
            return True

        if self.site:
            if not self.parent:
                # only site admins can change root site folders
                return has_admin_role_on_site(user, self.site)
            return (user.has_perm('filer.delete_folder') and
                    has_role_on_site(user, self.site))

        return False

    class Meta:
        unique_together = (('parent', 'name'),)
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
