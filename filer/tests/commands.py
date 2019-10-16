""" Tests for management commdands. """
from io import StringIO
from datetime import datetime, timedelta

from django.test import TestCase
from django.core.management import call_command

from filer.models.foldermodels import Folder
from filer.models.filemodels import File
from filer.settings import FILER_TRASH_CLEAN_INTERVAL


class TestTakeOutTrashCommand(TestCase):
    """ Tests for the management command that clears the old items trash. """

    def setUp(self):
        # Regular files and folders
        self.root_dir = Folder.objects.create(name='root_dir')
        self.sub_dir = Folder.objects.create(name='sub_dir', parent=self.root_dir)
        self.leaf_dir = Folder.objects.create(name='leaf_dir')
        self.top_file = File.objects.create(original_filename="top_file")
        self.middle_file = File.objects.create(original_filename="middle_file", folder=self.sub_dir)
        self.bottom_file = File.objects.create(original_filename="bottom_file", folder=self.leaf_dir)

        self.now = datetime.now()
        self.limit_time = self.now - timedelta(seconds=FILER_TRASH_CLEAN_INTERVAL)
        self.long_ago = self.now - timedelta(days=1, seconds=FILER_TRASH_CLEAN_INTERVAL)

        # Recent trash (that can be restored)
        self.recent_del_top_dir = Folder.objects.create(
            name="recent_del_top_dir", deleted_at=self.limit_time + timedelta(days=1))
        self.recent_del_sub_dir = Folder.objects.create(
            name="recent_del_sub_dir", parent=self.recent_del_top_dir,
            deleted_at=self.limit_time + timedelta(hours=1))
        self.recent_del_empty_dir = Folder.objects.create(name="recent_del_empty_dir",
                                                          deleted_at=self.now)
        self.recent_del_top_file = File.objects.create(original_filename="recent_del_top_file",
                                                         deleted_at=self.now)
        self.recent_del_bottom_file = File.objects.create(
            original_filename="recent_del_bottom_file",
            deleted_at=self.limit_time + timedelta(days=2))

        # Old trash (should be deleted)
        self.old_del_dir = Folder.objects.create(name="old_del_dir", deleted_at=self.long_ago)
        self.old_del_sub_dir = Folder.objects.create(name="old_del_sub_dir",
                                                     parent=self.old_del_dir,
                                                     deleted_at=self.long_ago)
        self.old_del_empty_dir = Folder.objects.create(name="old_del_empty_dir",
                                                       deleted_at=self.long_ago)
        self.old_del_top_file = File.objects.create(original_filename="old_del_top_file",
                                                    deleted_at=self.long_ago)
        self.old_del_bottom_file = File.objects.create(original_filename="old_del_bottom_file",
                                                       deleted_at=self.long_ago)

    def test_trash_is_cleared(self):
        stdout, stderr = self.run_trash_command()
        self.assertEqual(stderr.getvalue(), "", "Errors found while running command!")
        stdout_val = stdout.getvalue()
        deleted_files = stdout_val.count("Deleting file")
        self.assertEqual(deleted_files, 2,
                         "Deleted unexpected number of files: " + str(deleted_files))
        deleted_folders = stdout_val.count("Deleting folder")
        self.assertEqual(deleted_folders, 3,
                         "Deleted unexpected number of folders: " + str(deleted_folders))
        self.assert_required_files_remain()
        self.assert_folder_does_not_exist("old_del_dir")
        self.assert_folder_does_not_exist("old_del_sub_dir")
        self.assert_folder_does_not_exist("old_del_empty_dir")
        self.assert_file_does_not_exist("old_del_top_file")
        self.assert_file_does_not_exist("old_del_bottom_file")

    def test_no_operation(self):
        File.trash.filter(deleted_at__lt=self.limit_time).delete()
        Folder.trash.filter(deleted_at__lt=self.limit_time).delete()
        stdout, stderr = self.run_trash_command()
        self.assertEqual(stdout.getvalue(), "No old files or folders.\n")
        self.assertEqual(stderr.getvalue(), "", "Errors found while running command!")
        self.assert_required_files_remain()

    def run_trash_command(self):
        stdout = StringIO()
        stderr = StringIO()
        call_command("take_out_filer_trash", stdout=stdout, stderr=stderr)
        return stdout, stderr

    def assert_required_files_remain(self):
        root_dir = Folder.objects.get(name="root_dir")
        sub_dir = Folder.objects.get(name="sub_dir", parent=root_dir)
        leaf_dir = Folder.objects.get(name="leaf_dir")
        File.objects.get(original_filename="top_file")
        File.objects.get(original_filename="middle_file", folder=sub_dir)
        File.objects.get(original_filename="bottom_file", folder=leaf_dir)

        recent_del_top_dir = Folder.all_objects.get(name="recent_del_top_dir")
        Folder.all_objects.get(name="recent_del_sub_dir", parent=recent_del_top_dir)
        Folder.all_objects.create(name="recent_del_empty_dir")
        File.all_objects.get(original_filename="recent_del_top_file")
        File.all_objects.get(original_filename="recent_del_bottom_file")

    def assert_folder_does_not_exist(self, folder_name):
        with self.assertRaises(Folder.DoesNotExist):
            Folder.all_objects.get(name=folder_name)

    def assert_file_does_not_exist(self, file_name):
        with self.assertRaises(File.DoesNotExist):
            File.all_objects.get(original_filename=file_name)

