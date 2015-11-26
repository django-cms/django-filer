# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import inspect
import os
from collections import namedtuple
from optparse import make_option

from django.core.files.storage import FileSystemStorage, get_storage_class
from django.core.management.base import BaseCommand, CommandError

from ... import settings as filer_settings
from ...models.filemodels import File
from ...models.foldermodels import Folder
from ...utils.compatibility import upath
from ...utils.loader import load_object

_dup_actions = ['overwrite', 'skip', 'update', 'new']
DuplicateActions = namedtuple('DuplicateActions', _dup_actions)
DUPLICATE_ACTIONS = DuplicateActions(*_dup_actions)


def normpath(path, no_dots=True, expand_user=False):
    if not path:
        return ''
    ret_path = path
    if expand_user:
        ret_path = os.path.expanduser(upath(ret_path))
    ret_path = os.path.normpath(ret_path)
    if no_dots and ret_path.startswith('.'):
        raise CommandError("Path '%s'->'%s' cannot be '.' or be relatively up (start with '..')" % (path, ret_path))
    return ret_path


class FileImporter(object):
    def __init__(self, path, base_folder, storage_class, dup_action, verbosity=1, **kwargs):
        base_folder = normpath(base_folder)
        stor_kwargs = {}
        if path:
            stor_kwargs['location'] = path
        self.storage = storage_class(**stor_kwargs)
        self.dup_action = dup_action
        self.verbosity = int(verbosity)
        self.files_created = {}  # mapping of <file class>:<how many have been created>
        self.folder_created = 0
        self.target_folder = None
        folder_name = 'root folder'
        if base_folder:
            self.target_folder = self.get_or_create_folder(base_folder.split('/'))
            folder_name = "folder '%s'" % base_folder
        print("Selected paths will be imported into filer's %s" % folder_name)

    def import_file(self, file_obj, folder, file_path):
        """
        Create a File or an Image into the given folder
        """

        def del_orphan_file(obj):
            # Delete the file if there are no other Files referencing it.
            qs = File.objects.exclude(pk=obj.pk)
            if not qs.filter(file=obj.file.name, is_public=obj.is_public).exists():
                obj.file.delete(False)

        basename = os.path.basename(file_obj.name)
        # find the file type
        for filer_class in filer_settings.FILER_FILE_MODELS:
            FileSubClass = load_object(filer_class)
            # TODO: What if there are more than one that qualify?
            if FileSubClass.matches_file_type(basename, None, None):
                obj = FileSubClass(
                    original_filename=basename,
                    file=file_obj,
                    folder=folder,
                    is_public=filer_settings.FILER_IS_PUBLIC_DEFAULT)
                class_name = FileSubClass.__name__
                if class_name not in self.files_created:
                    self.files_created[class_name] = 0
                break
        # check if such file was already imported in this folder
        duplicates = folder.all_files.filter(
            original_filename__exact=basename)
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
                obj.generate_sha1()  # generate sha1 now to compare
                diff_sha_q = duplicates.exclude(sha1__exact=obj.sha1)
                if not diff_sha_q.count():
                    return None  # no need to update, skip
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

    def import_path(self, path):
        path = normpath(path)
        if self.verbosity >= 1:
            print("Import the folders and files in %s" % (path,))
        target_folder = self.get_or_create_folder(path.split('/'), self.target_folder)
        self._import_dir(path, target_folder)

    def _import_dir(self, path, folder):
        dirs, files = self.storage.listdir(path)
        for dir in dirs:
            child_folder = self.get_or_create_folder((dir,), folder)
            self._import_dir(os.path.join(path, dir), child_folder)
        for file in files:
            file_path = os.path.join(path, file)
            with self.storage.open(file_path) as dj_file:
                self.import_file(dj_file, folder, file_path)
        if self.verbosity >= 1:
            self._print_created()


class Command(BaseCommand):
    """
    Import directory structure into the filer ::

        manage.py import_files --path=/tmp/assets/images folder
        manage.py import_files --path=/tmp/assets/news --folder=images other_folder
        manage.py import_files --folder=a --storage=storages.backends.ftp.FTPStorage public_html
        manage.py import_files --path=/tmp/assets/news --duplicate-action=update images content something
    """

    help = __doc__
    args = "<path_to_import path_to_import ...>"
    option_list = BaseCommand.option_list + (
        make_option('--path',
            action='store',
            dest='path',
            default='',
            help='Import paths starting at this base path. This is a current directory by default'),
        make_option('--folder',
            action='store',
            dest='base_folder',
            default='',
            help='Specify the destination folder in which paths should be imported'),
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
            help='Specify constanct action when duplicate file is found in Filer '
                 '(one of %s)' % list(DUPLICATE_ACTIONS)),
    )

    def handle(self, *paths, **options):
        if not len(paths):
            raise CommandError('No paths to import provided!')
        options['storage_class'] = get_storage_class(options['storage_class'])
        stor_is_filesystem = (inspect.isclass(options['storage_class']) and
                             issubclass(options['storage_class'], FileSystemStorage))
        if options['path']:
            options['path'] = normpath(options['path'],
                                       no_dots=not stor_is_filesystem,
                                       expand_user=not stor_is_filesystem)
        elif stor_is_filesystem:
            # FileSystemStorage defaults to MEDIA_ROOT setting for location
            # this is not a good default in this case, use current directory instead
            options['path'] = os.getcwd()
        file_importer = FileImporter(**options)
        for path in paths:
            file_importer.import_path(path)
