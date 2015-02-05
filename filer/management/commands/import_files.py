# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from optparse import make_option

from django.core.files import File as DjangoFile
from django.core.management.base import BaseCommand, NoArgsCommand

from ... import settings as filer_settings
from ...models.foldermodels import Folder
from ...utils.compatibility import upath


class FileImporter(object):
    def __init__(self, * args, **kwargs):
        self.path = kwargs.get('path')
        self.base_folder = kwargs.get('base_folder')
        self.verbosity = int(kwargs.get('verbosity', 1))
        self.files_created = {}  # mapping of <file class>:<how many have been created>
        self.folder_created = 0

    def import_file(self, file_obj, folder):
        """
        Create a File or an Image into the given folder
        """
        # find the file type
        for filer_class in filer_settings.FILER_FILE_MODELS:
            FileSubClass = load_object(filer_class)
            # TODO: What if there are more than one that qualify?
            if FileSubClass.matches_file_type(file_obj.name, None, None):
                obj = FileSubClass.objects.create(
                    original_filename=file_obj.name,
                    file=file_obj,
                    folder=folder,
                    is_public=filer_settings.FILER_IS_PUBLIC_DEFAULT)
                class_name = FileSubClass.__name__
                if class_name not in self.files_created:
                    self.files_created[class_name] = 0
                self.files_created[class_name] += 1
                break
        if self.verbosity >= 2:
            self._print_created('-- file : %s' % obj)
        return obj

    def _print_created(self, add=''):
        file_count = sum(self.files_created.values())
        file_types = ['%s: %d' % (k, v) for k, v in self.files_created.items()]
        print('Files created: %d (%s) / folders created: %d %s' % (
            file_count,
            ', '.join(file_types),
            self.folder_created,
            add))

    def get_or_create_folder(self, folder_names):
        """
        Gets or creates a Folder based the list of folder names in hierarchical
        order (like breadcrumbs).

        get_or_create_folder(['root', 'subfolder', 'subsub folder'])

        creates the folders with correct parent relations and returns the
        'subsub folder' instance.
        """
        if not len(folder_names):
            return None
        current_parent = None
        for folder_name in folder_names:
            current_parent, created = Folder.objects.get_or_create(name=folder_name, parent=current_parent)
            if created:
                self.folder_created += 1
                if self.verbosity >= 2:
                    self._print_created('%s -- created : %s' % (current_parent, created))
        return current_parent

    def walker(self, path=None, base_folder=None):
        """
        This method walk a directory structure and create the
        Folders and Files as they appear.
        """
        path = path or self.path
        base_folder = base_folder or self.base_folder
        # prevent trailing slashes and other inconsistencies on path.
        path = os.path.normpath(upath(path))
        if base_folder:
            base_folder = os.path.normpath(upath(base_folder))
            print("The directory structure will be imported in %s" % (base_folder,))
        if self.verbosity >= 1:
            print("Import the folders and files in %s" % (path,))
        root_folder_name = os.path.basename(path)
        for root, dirs, files in os.walk(path):
            rel_folders = root.partition(path)[2].strip(os.path.sep).split(os.path.sep)
            while '' in rel_folders:
                rel_folders.remove('')
            if base_folder:
                folder_names = base_folder.split('/') + [root_folder_name] + rel_folders
            else:
                folder_names = [root_folder_name] + rel_folders
            folder = self.get_or_create_folder(folder_names)
            for file_obj in files:
                dj_file = DjangoFile(open(os.path.join(root, file_obj), mode='rb'),
                                     name=file_obj)
                self.import_file(file_obj=dj_file, folder=folder)
        if self.verbosity >= 1:
            self._print_created()


class Command(NoArgsCommand):
    """
    Import directory structure into the filer ::

        manage.py --path=/tmp/assets/images
        manage.py --path=/tmp/assets/news --folder=images
    """

    option_list = BaseCommand.option_list + (
        make_option('--path',
            action='store',
            dest='path',
            default=False,
            help='Import files located in the path into django-filer'),
        make_option('--folder',
            action='store',
            dest='base_folder',
            default=False,
            help='Specify the destination folder in which the directory structure should be imported'),
    )

    def handle_noargs(self, **options):
        file_importer = FileImporter(**options)
        file_importer.walker()

