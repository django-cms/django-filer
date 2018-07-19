# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.core import urlresolvers
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from . import mixins
from .. import settings as filer_settings
from .filemodels import File
from .foldermodels import Folder


class DummyFolder(mixins.IconsMixin):
    file_type = 'DummyFolder'
    name = "Dummy Folder"
    is_root = True
    is_smart_folder = True
    can_have_subfolders = False
    parent = None
    _icon = "plainfolder"

    @property
    def virtual_folders(self):
        return {}

    def get_virtual_folder(self, slug):
        return

    @property
    def children(self):
        return Folder.objects.none()

    @property
    def files(self):
        return File.objects.none()
    parent_url = None

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


class UnsortedImages(DummyFolder):
    name = _("Unsorted Uploads")
    is_root = True
    is_unsorted_uploads = True
    _icon = "unfiled_folder"

    def _files(self):
        return File.objects.filter(folder__isnull=True)
    files = property(_files)

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse(
            'admin:filer-directory_listing-unfiled_images')


class ImagesWithMissingData(DummyFolder):
    name = _("files with missing metadata")
    is_root = True
    _icon = "incomplete_metadata_folder"

    @property
    def files(self):
        return File.objects.filter(has_all_mandatory_data=False)

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse(
            'admin:filer-directory_listing-images_with_missing_data')


class FolderRoot(DummyFolder):
    name = _('root')
    is_root = True
    is_smart_folder = False
    can_have_subfolders = True

    @cached_property
    def virtual_folders(self):
        return {
            'unfiled_images': UnsortedImages(),
        }

    def get_virtual_folder(self, slug):
        return self.virtual_folders.get(slug)

    @property
    def children(self):
        # FIXME: this doesn't make much sense because in FolderAdmin.directory_listing parent__isnull=False
        # is excluded, so it's the same as if this 'if' did not exist...
        if filer_settings.FILER_ENABLE_PERMISSIONS:
            return Folder.objects.all()
        return Folder.objects.filter(parent__isnull=True)
    parent_url = None

    def contains_folder(self, folder_name):
        # FIXME: when filer_settings.FILER_ENABLE_PERMISSIONS is True, this doesn't work properly :)
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing-root')
