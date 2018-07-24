# -*- coding: utf-8 -*-

from __future__ import absolute_import

import warnings
from collections import OrderedDict

from django.core import urlresolvers
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from . import mixins
from .. import settings as filer_settings
from .filemodels import File
from .foldermodels import Folder, FolderPermission


class DummyFolder(mixins.IconsMixin):
    file_type = 'DummyFolder'
    name = "Dummy Folder"
    slug = None
    is_root = True
    is_smart_folder = True
    can_have_subfolders = False
    parent = None
    _icon = "plainfolder"
    virtual_folder_classes = []

    def __eq__(self, other):
        return self.__class__ == other.__class__

    @cached_property
    def virtual_folders(self):
        return OrderedDict((f.slug, f()) for f in self.virtual_folder_classes)

    @property
    def children(self):
        warnings.warn("'children' property on virtual folders should not be used. "
                      "Use 'get_children_for_user' instead.",
                      DeprecationWarning, stacklevel=2)
        return Folder.objects.none()

    def get_children_for_user(self, user):
        return Folder.objects.none()

    @property
    def files(self):
        return File.objects.none()

    def get_files_for_user(self, user):
        return self.files.filter_for_user(user)

    @property
    def image_files(self):
        return self.files

    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        return []

    def get_admin_directory_listing_url_path(self):
        if self.slug is None:
            return
        return urlresolvers.reverse(
            'admin:filer-directory_listing-%s' % self.slug)


class UnsortedImages(DummyFolder):
    name = _("Unsorted Uploads")
    slug = 'unfiled_images'
    is_root = True
    is_unsorted_uploads = True
    _icon = "unfiled_folder"

    def _files(self):
        return File.objects.filter(folder__isnull=True)
    files = property(_files)


class ImagesWithMissingData(DummyFolder):
    name = _("files with missing metadata")
    slug = 'images_with_missing_data'
    is_root = True
    _icon = "incomplete_metadata_folder"

    @property
    def files(self):
        return File.objects.filter(has_all_mandatory_data=False)


class FolderRoot(DummyFolder):
    name = _('root')
    slug = 'root'
    is_root = True
    is_smart_folder = False
    can_have_subfolders = True
    virtual_folder_classes = [UnsortedImages]

    @property
    def children(self):
        warnings.warn("'children' property on virtual folders should not be used. "
                      "Use 'get_children_for_user' instead.",
                      DeprecationWarning, stacklevel=2)
        if filer_settings.FILER_ENABLE_PERMISSIONS:
            return Folder.objects.all()
        return Folder.objects.filter(parent__isnull=True)

    def get_children_for_user(self, user):
        perms = FolderPermission.objects.get_read_id_list(user)
        if perms != 'All':
            qs = Folder.objects.filter_for_user(user)
            # get folders which are in root or user has only indirect access to (permission for nested folder
            # but not it's parent)
            return qs.exclude(Q(parent__isnull=False) & (Q(parent__id__in=perms) | Q(parent__owner=user)))
        return Folder.objects.filter(parent__isnull=True)

    def get_default_folder(self, file_model=None):
        """
        Returns default virtual folder for File (sub)model.
        Default implementation always returns UnsortedImages virtual folder.
        This is used mostly for redirecting to relevant directory listing after various actions
        in admin.
        """
        return self.virtual_folders['unfiled_images']

    def contains_folder(self, folder_name):
        try:
            Folder.objects.filter(parent__isnull=True).get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False
