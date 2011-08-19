#-*- coding: utf-8 -*-
from django.core import urlresolvers
from django.utils.translation import ugettext_lazy as _
from filer.models import mixins
from filer.models.filemodels import File
from filer.models.foldermodels import Folder


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
        return []

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


class UnfiledImages(DummyFolder):
    name = _("unfiled files")
    is_root = True
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

    @property
    def virtual_folders(self):
        return [UnfiledImages()]

    @property
    def children(self):
        return Folder.objects.filter(parent__isnull=True)
    parent_url = None

    def contains_folder(self, folder_name):
        try:
            self.children.get(name=folder_name)
            return True
        except Folder.DoesNotExist:
            return False

    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing-root')
