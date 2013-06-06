"""
Archiving support for filer.
"""
from filer.models.filemodels import File, Folder
from django.utils.translation import ugettext_lazy as _
from django.core.files.base import ContentFile
from django.db.models import Q
from filer.settings import FILER_IS_PUBLIC_DEFAULT, FILER_FILE_MODELS
from filer.utils.loader import load_object
from filer.utils.files import matching_file_subtypes

import os.path
import zipfile


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

    def extract(self, bypass_owner=False):
        """Extracts the archive files' contents."""
        self.file.open()
        try:
            self._extract_zip(self.file, bypass_owner)
        finally:
            self.file.close()

    def is_valid(self):
        """Checks if the file is a proper archive."""
        is_valid = False
        self.file.open()
        try:
            is_valid = self._is_valid_zip(self.file)
        finally:
            self.file.close()
        return is_valid

    def collisions(self):
        """
        Verifies that the files or folders about to be written don't already
        exist.
        Returns any duplicated files/folders.
        """
        in_both = []
        self.file.open()
        try:
            in_both = self._collisions_zip(self.file)
        finally:
            self.file.close()
        return in_both

    def _is_valid_zip(self, filer_file):
        """Validates zip files."""
        is_valid = zipfile.is_zipfile(filer_file)
        return is_valid

    def _collisions_zip(self, filer_file):
        """Checks collisions for zip files."""
        zippy = zipfile.ZipFile(filer_file)
        cwd = self.logical_folder
        if cwd.is_root:
            cwd_path = os.sep
            orphan_files = [x.pretty_logical_path
                            for x in File.objects.filter(folder=None)]
            orphan_folders = [x.pretty_logical_path
                              for x in Folder.objects.filter(parent=None)]
            filer_paths = orphan_files + orphan_folders
        else:
            cwd_path = cwd.pretty_logical_path + os.sep
            filer_paths = cwd.pretty_path_entries()
        zip_paths = [cwd_path + x.rstrip(os.sep).decode('utf8')
                     for x in zippy.namelist()]
        file_set = set(filer_paths)
        intersection = [x for x in zip_paths if x in file_set]
        return intersection

    def _extract_zip(self, filer_file, bypass_owner=False):
        """
        Creates the file and folder hierarchy from the contents of the zip
        file. It first creates the parent folder of the selected file if it
        does not already exist, similair to mkdir -p.
        """
        zippy = zipfile.ZipFile(filer_file)
        entries = zippy.infolist()
        for entry in entries:
            full_path = entry.filename.decode('utf8')
            filename = os.path.basename(full_path)
            parent_dir = self._create_parent_folders(full_path, bypass_owner)
            if filename:
                data = zippy.read(entry)
                self._create_file(filename, parent_dir, data, bypass_owner)

    def _create_parent_folders(self, full_path, bypass_owner=False):
        """Creates the folder parents for a given entry."""
        dir_parents_of_entry = full_path.split(os.sep)[:-1]
        parent_dir = self.folder
        for directory_name in dir_parents_of_entry:
            parent_dir = self._create_folder(
                directory_name, parent_dir, bypass_owner)
        return parent_dir

    def _create_folder(self, name, parent, bypass_owner=False):
        """
        Helper wrapper of creating a file in a filer folder.
        If there already is a folder with the given name, it returnes that.
        """
        attrs = dict(name=name, parent=parent)
        if bypass_owner is False:
            attrs['owner'] = self.owner

        existing = Folder.objects.filter(**attrs)
        if existing:
            return existing[0]
        # make sure owner is set
        attrs['owner'] = self.owner
        return Folder.objects.create(**attrs)

    def _create_file(self, basename, folder, data, bypass_owner=False):
        """Helper wrapper of creating a filer file."""
        file_data = ContentFile(data)
        file_data.name = basename
        matched_file_types = matching_file_subtypes(basename, None, None)
        FileSubClass = matched_file_types[0]
        file_manager = FileSubClass.objects

        name_query = (Q(original_filename=basename) & (
            Q(name__isnull=True) | Q(name__exact=''))) | Q(name=basename)

        search_query = Q(folder=folder) & name_query

        if bypass_owner is False:
            search_query &= Q(owner=self.owner)

        existing = file_manager.filter(search_query)
        file_object = None
        if existing:
            file_object = existing[0]
            file_object.name = None
            file_object.original_filename = basename
            file_object.file = file_data
            file_object.save()
        else:
            file_object = file_manager.create(
                original_filename=basename,
                folder=folder,
                owner=self.owner,
                file=file_data,
                is_public=FILER_IS_PUBLIC_DEFAULT,
            )
        return file_object

    class Meta:
        """Meta information for filer file model."""
        app_label = 'filer'
        verbose_name = _('archive')
        verbose_name_plural = _('archives')
