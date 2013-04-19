#-*- coding: utf-8 -*-
from django.core.files import File as DjangoFile
from django.http import HttpRequest
from django.test.testcases import TestCase
from filer.models import tools
from filer.models.clipboardmodels import Clipboard
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.tests.helpers import create_superuser, create_image
import os

class ToolsTestCase(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename), name=self.image_name)
        # This is actually a "file" for filer considerations
        self.image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=self.file)
        self.clipboard = Clipboard.objects.create(user=self.superuser)
        self.clipboard.append_file(self.image)

        self.folder = Folder.objects.create(name='test_folder')

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for img in Image.objects.all():
            os.remove(img.file.path)
            img.delete()

    def test_clear_clipboard_works(self):
        self.assertEqual(len(self.clipboard.files.all()), 1)
        tools.discard_clipboard(self.clipboard)
        self.assertEqual(len(self.clipboard.files.all()), 0)

    def test_move_to_clipboard_works(self):
        self.assertEqual(len(self.clipboard.files.all()), 1)

        file2 = Image.objects.create(owner=self.superuser,
                                     original_filename='file2',
                                     file=self.file)
        file3 = Image.objects.create(owner=self.superuser,
                                     original_filename='file3',
                                     file=self.file)
        files = [file2, file3]
        request = HttpRequest()
        tools.move_file_to_clipboard(request, files, self.clipboard)
        self.assertEqual(len(self.clipboard.files.all()), 3)

    def test_move_from_clipboard_to_folder_works(self):
        self.assertEqual(len(self.clipboard.files.all()), 1)
        request = HttpRequest()
        tools.move_files_from_clipboard_to_folder(request, self.clipboard, self.folder)
        for file in self.clipboard.files.all():
            self.assertEqual(file.folder, self.folder)

    def test_delete_clipboard_works(self):
        self.assertEqual(len(self.clipboard.files.all()), 1)

        tools.delete_clipboard(self.clipboard)
        # Assert there is no file with self.image_name = 'test_file.jpg'
        result = Image.objects.filter(file=self.file)
        self.assertEqual(len(result), 0)
