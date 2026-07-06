"""Tests for filer.models.tools."""

from django.test import TestCase

from filer.models.clipboardmodels import Clipboard, ClipboardItem
from filer.models.filemodels import File
from filer.models.foldermodels import Folder
from filer.models.tools import (
    delete_clipboard,
    discard_clipboard,
    get_user_clipboard,
    move_file_to_clipboard,
    move_files_from_clipboard_to_folder,
    move_files_to_folder,
)
from tests.helpers import create_superuser


class ClipboardToolsTests(TestCase):
    """Tests for clipboard tool functions."""

    def setUp(self):
        self.user = create_superuser()
        self.clipboard = Clipboard.objects.create(user=self.user)

        from django.core.files.uploadedfile import SimpleUploadedFile
        obj = SimpleUploadedFile(name='test.txt', content=b'test',
                                  content_type='text/plain')
        self.file1 = File.objects.create(
            owner=self.user, file=obj,
            original_filename='test.txt', is_public=True,
        )

    def test_discard_clipboard(self):
        ClipboardItem.objects.create(clipboard=self.clipboard, file=self.file1)
        self.assertEqual(self.clipboard.files.count(), 1)
        discard_clipboard(self.clipboard)
        self.assertEqual(self.clipboard.files.count(), 0)

    def test_delete_clipboard(self):
        ClipboardItem.objects.create(clipboard=self.clipboard, file=self.file1)
        self.assertEqual(File.objects.filter(pk=self.file1.pk).count(), 1)
        delete_clipboard(self.clipboard)
        self.assertEqual(File.objects.filter(pk=self.file1.pk).count(), 0)

    def test_get_user_clipboard(self):
        clipboard = get_user_clipboard(self.user)
        self.assertIsNotNone(clipboard)
        self.assertEqual(clipboard.user, self.user)

    def test_get_user_clipboard_idempotent(self):
        c1 = get_user_clipboard(self.user)
        c2 = get_user_clipboard(self.user)
        self.assertEqual(c1.pk, c2.pk)

    def test_move_file_to_clipboard(self):
        folder = Folder.objects.create(name='test_folder')
        self.file1.folder = folder
        self.file1.save()
        count = move_file_to_clipboard([self.file1], self.clipboard)
        self.assertEqual(count, 1)
        self.file1.refresh_from_db()
        self.assertIsNone(self.file1.folder)

    def test_move_file_to_clipboard_already_present(self):
        move_file_to_clipboard([self.file1], self.clipboard)
        count = move_file_to_clipboard([self.file1], self.clipboard)
        self.assertEqual(count, 0)

    def test_move_files_to_folder(self):
        folder = Folder.objects.create(name='target')
        move_files_to_folder([self.file1], folder)
        self.file1.refresh_from_db()
        self.assertEqual(self.file1.folder, folder)

    def test_move_files_from_clipboard_to_folder(self):
        ClipboardItem.objects.create(clipboard=self.clipboard, file=self.file1)
        folder = Folder.objects.create(name='target')
        move_files_from_clipboard_to_folder(self.clipboard, folder)
        self.file1.refresh_from_db()
        self.assertEqual(self.file1.folder, folder)
