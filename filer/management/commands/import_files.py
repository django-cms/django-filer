# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os
from collections import namedtuple
from optparse import make_option

from django.core.files.storage import get_storage_class
from django.core.management.base import BaseCommand, NoArgsCommand

from ... import settings as filer_settings
from ...models.filemodels import File
from ...models.foldermodels import Folder
from ...utils.compatibility import upath
from ...utils.loader import load_object

_dup_actions = ['overwrite', 'skip', 'update', 'new']
DuplicateActions = namedtuple('DuplicateActions', _dup_actions)
DUPLICATE_ACTIONS = DuplicateActions(*_dup_actions)


class FileImporter(object):
    def __init__(self, * args, **kwargs):
        self.path = kwargs.get('path') or ''
        self.base_folder = kwargs.get('base_folder') or ''
        # prevent trailing slashes and other inconsistencies on path.
        self.path = os.path.expanduser(upath(self.path))
        self.path = os.path.normpath(self.path)
        self.base_folder = os.path.normpath(upath(self.base_folder))
        self.storage = kwargs.get('storage_class')(location=self.path)
        self.dup_action = kwargs.get('dup_action')
        self.verbosity = int(kwargs.get('verbosity', 1))
        self.files_created = {}  # mapping of <file class>:<how many have been created>
        self.folder_created = 0

    def import_file(self, file_obj, folder, file_path):
        """
        Create a File or an Image into the given folder
        """

        def del_orphan_file(obj):
            # Delete the file if there are no other Files referencing it.
            qs = File.objects.exclude(pk=obj.pk)
            if not qs.filter(file=obj.file.name, is_public=obj.is_public).exists():
                obj.file.delete(False)

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
                break
        # check if such file was already imported in this folder
        duplicates = folder.all_files.filter(
                        original_filename__exact=file_obj.name)
        if self.dup_action != DUPLICATE_ACTIONS.new and duplicates.count():
            dup_action = self.dup_action
            if dup_action is None:
                # no default duplicate action provided, do interactive choice
                print('A matching file already exists in Filer (same original filename and folder)'
                      ' for source file: %s' % file_path)
                dup_action = ''
                while dup_action.lower() not in DUPLICATE_ACTIONS:
                    dup_action = input('Choose action from %s:' % list(DUPLICATE_ACTIONS))
            if dup_action == DUPLICATE_ACTIONS.skip:
                return None
            if dup_action == DUPLICATE_ACTIONS.overwrite:
                obj = duplicates.first()
                del_orphan_file(obj)
                obj.file = file_obj
            elif dup_action == DUPLICATE_ACTIONS.update:
                obj.generate_sha1() # generate sha1 now to compare
                diff_sha_q = duplicates.exclude(sha1__exact=obj.sha1)
                if not diff_sha_q.count():
                    return None # no need to update, skip
                obj = diff_sha_q.first()
                del_orphan_file(obj)
                obj.file = file_obj

        obj.save()
        self.files_created[class_name] += 1
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
            file_path = os.path.join(path, file)
            with self.storage.open(file_path) as dj_file:
                self.import_file(dj_file, target_folder, file_path)

    def walker(self):
        """
        This method walks a directory structure and creates
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

        manage.py import_files --path=/tmp/assets/images
        manage.py import_files --path=/tmp/assets/news --folder=images
        manage.py import_files --path=/tmp --folder=a --storage=storages.backends.ftp.FTPStorage
        manage.py import_files --path=/tmp/assets/news --folder=images --duplicate-action=update
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
        make_option('--duplicate-action',
            action='store',
            type='choice',
            choices=DUPLICATE_ACTIONS,
            dest='dup_action',
            default=None,
            help='Specify constanct action when duplicate file is already found in Filer '
                 '(one of %s)' % list(DUPLICATE_ACTIONS)),
        )

    def handle_noargs(self, **options):
        options['storage_class'] = get_storage_class(options['storage_class'])
        file_importer = FileImporter(**options)
        file_importer.walker()

