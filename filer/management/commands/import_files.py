# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from optparse import make_option

from django.core.files.storage import get_storage_class
from django.core.management.base import BaseCommand, NoArgsCommand

from ... import settings as filer_settings
from ...models.foldermodels import Folder
from ...utils.compatibility import upath
from ...utils.loader import load_object


class FileImporter(object):
    def __init__(self, * args, **kwargs):
        self.path = kwargs.get('path') or ''
        self.base_folder = kwargs.get('base_folder') or ''
        # prevent trailing slashes and other inconsistencies on path.
        self.path = os.path.expanduser(upath(self.path))
        self.path = os.path.normpath(self.path)
        self.base_folder = os.path.normpath(upath(self.base_folder))
        self.storage = kwargs.get('storage_class')(self.path)
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

    def get_or_create_folder(self, folder_names, parent=None):
        """
        Gets or creates a Folder based the list of folder names in hierarchical
        order (like breadcrumbs) starting at parent folder (if specified) or root.

        get_or_create_folder(['root', 'subfolder', 'subsub folder'], parent)

        creates the folders with correct parent relations and returns the
        'subsub folder' instance.
        """
        if not len(folder_names):
            return None
        for folder_name in folder_names:
            parent, created = Folder.objects.get_or_create(name=folder_name, parent=parent)
            if created:
                self.folder_created += 1
                if self.verbosity >= 2:
                    self._print_created('%s -- created : %s' % (parent, created))
        return parent

    def _import_dir(self, path, target_folder):
        dirs, files = self.storage.listdir(path)
        for dir in dirs:
            folder = self.get_or_create_folder((dir,), target_folder)
            self._import_dir(os.path.join(path, dir), folder)
        for file in files:
            with self.storage.open(os.path.join(path, file)) as dj_file:
                self.import_file(dj_file, target_folder)

    def walker(self):
        """
        This method walk a directory structure and create the
        Folders and Files as they appear.
        """
        print("The directory structure will be imported in %s" % (self.base_folder,))
        if self.verbosity >= 1:
            print("Import the folders and files in %s" % (self.path,))
        target_folder = self.get_or_create_folder(self.base_folder.split('/'))
        self._import_dir('', target_folder)
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
            default=None,
            help='Import files located in the path into django-filer'),
        make_option('--folder',
            action='store',
            dest='base_folder',
            default=None,
            help='Specify the destination folder in which the directory structure should be imported'),
        make_option('--storage',
            action='store',
            dest='storage_class',
            default=None,
            help='Specify a storage class to use for retrieving files instead of default storage'),
    )

    def handle_noargs(self, **options):
        options['storage_class'] = get_storage_class(options['storage_class'])
        file_importer = FileImporter(**options)
        file_importer.walker()

