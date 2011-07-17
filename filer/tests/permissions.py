#-*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase
from filer import settings as filer_settings
from filer.models.clipboardmodels import Clipboard
from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.tests.utils import Mock
from filer.tests.helpers import create_image, create_superuser
import os

class FolderPermissionsTestCase(TestCase):

    def create_fixtures(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')

        self.unauth_user = User.objects.create(username='test1')

        self.owner = User.objects.create(username='owner')

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

    def test_superuser_has_rights(self):
        self.create_fixtures()
        request = Mock()
        setattr(request, 'user', self.superuser)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_unlogged_user_has_no_rights(self):
        old_setting = filer_settings.FILER_ENABLE_PERMISSIONS
        filer_settings.FILER_ENABLE_PERMISSIONS = True
        self.create_fixtures()
        request = Mock()
        setattr(request, 'user', self.unauth_user)

        result = self.folder.has_read_permission(request)
        filer_settings.FILER_ENABLE_PERMISSIONS = old_setting
        self.assertEqual(result, False)

    def test_unlogged_user_has_rights_when_permissions_disabled(self):
        self.create_fixtures()
        request = Mock()
        setattr(request, 'user', self.unauth_user)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)

    def test_owner_user_has_rights(self):
        self.create_fixtures()
        # Set owner as the owner of the folder.
        self.folder.owner = self.owner
        request = Mock()
        setattr(request, 'user', self.owner)

        result = self.folder.has_read_permission(request)
        self.assertEqual(result, True)
