"""
Archiving support for filer.
"""
from filer.models.filemodels import File, Folder
from django.utils.translation import ugettext_lazy as _
from django.core.files.base import ContentFile
from filer.settings import FILER_IS_PUBLIC_DEFAULT

import os.path
import zipfile


def folder_entries(folder):
    """Returns the subentries of 'folder' in the slashed form."""
    subdirs = folder.get_descendants()
    subdir_files = [x.files for x in subdirs]
    subdir_files += [folder.files]
    flatten = lambda superlist, files: list(superlist) + list(files)
    super_files = reduce(flatten, subdir_files)
    file_paths = map(get_logical_path, super_files)
    dir_paths = map(get_logical_path, subdirs)
    paths = file_paths + dir_paths
    return paths


def get_logical_path(entry):
    """Returns the slashed logical path form."""
    parents = [x.name for x in entry.logical_path]
    is_a_dir = lambda: entry.file_type == 'Folder'
    path = os.sep.join([''] + parents + [entry.actual_name])
    if is_a_dir():
        path += os.sep
    return path


class Archive(File):
    """
    Django model for manipulating archive files.
    With extract, it creates the file structure from within a archive file.
    Current supported archive file types: zip.
    """
    file_type = 'Archive'
    _icon = 'archive'
    _filename_extensions = ['.zip', ]

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        """Checks if the file has an archive type extension."""
        extension = os.path.splitext(iname)[-1].lower()
        return extension in Archive._filename_extensions

    def extract(self):
        """Extracts the archive files' contents."""
        self._extract_zip(self.file)

    def validate(self):
        """
        Verifies that the files or folders  about to be written don't already
        exist.
        Returns any duplicated files/folders.
        """
        return self._validate_zip(self.file)

    def _validate_zip(self, filer_file):
        """Validates zip files."""
        zippy = zipfile.ZipFile(filer_file)
        cwd = self.logical_folder
        cwd_path = get_logical_path(cwd)
        zip_paths = [cwd_path + x for x in zippy.namelist()]
        filer_paths = folder_entries(cwd)
        intersection = [x for x in filer_paths if x in zip_paths]
        return intersection

    def _extract_zip(self, filer_file):
        """
        Creates the file and folder hierarchy from the contents of the zip
        file. It first creates the parent folder of the selected file if it
        does not already exist, similair to mkdir -p.
        """
        zippy = zipfile.ZipFile(filer_file)
        entries = zippy.infolist()
        for entry in entries:
            parent_dir = self._create_parent_folders(entry)
            filename = os.path.basename(entry.filename)
            if filename:
                data = zippy.read(entry)
                self._create_file(filename, parent_dir, data)
        zippy.close()
        filer_file.close()

    def _create_parent_folders(self, entry):
        """Creates the folder parents for a given entry."""
        dir_parents_of_entry = entry.filename.split(os.sep)[:-1]
        parent_dir = self.folder
        for directory_name in dir_parents_of_entry:
            parent_dir = self._create_folder(directory_name, parent_dir)
        return parent_dir

    def _create_folder(self, name, parent):
        """
        Helper wrapper of creating a file in a filer folder.
        If there already is a folder with the given name, it returnes that.
        """
        current_dir, created = Folder.objects.get_or_create(
            name=name,
            parent=parent,
            owner=self.owner,
        )
        return current_dir

    def _create_file(self, basename, folder, data):
        """Helper wrapper of creating a filer file."""
        file_data = ContentFile(data)
        file_data.name = basename
        file_object, created = File.objects.get_or_create(
            original_filename=file_data.name,
            folder=folder,
            owner=self.owner,
            file=file_data,
            is_public=FILER_IS_PUBLIC_DEFAULT,
        )
        file_data.close()
        return file_object

    class Meta:
        """Meta information for filer file model."""
        app_label = 'filer'
        verbose_name = _('archive')
        verbose_name_plural = _('archives')
