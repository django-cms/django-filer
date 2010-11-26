import os
from django.test import TestCase
from django.core.files import File as DjangoFile

from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.models.clipboardmodels import Clipboard
from filer.admin.clipboardadmin import UploadImageFileForm
from filer.tests.helpers import (create_superuser, create_folder_structure,
                                 create_image, create_clipboard_item)
from filer import settings as filer_settings



class FilerApiTests(TestCase):
    
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(os.path.dirname(__file__),
                                 self.image_name)
        self.img.save(self.filename, 'JPEG')
        
    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for img in Image.objects.all():
            img.delete()
            
    def create_filer_image(self):
        file = DjangoFile(open(self.filename), name=self.image_name)
        image = Image.objects.create(owner=self.superuser,
                                     original_filename=self.image_name,
                                     file=file)
        return image
            
    def test_create_folder_structure(self):
        create_folder_structure(depth=3, sibling=2, parent=None)
        self.assertEqual(Folder.objects.count(), 26)
        
    def test_create_and_delete_image(self):
        self.assertEqual(Image.objects.count(), 0)
        image = self.create_filer_image()
        image.save()
        self.assertEqual(Image.objects.count(), 1)
        image = Image.objects.all()[0]
        image.delete()
        self.assertEqual(Image.objects.count(), 0)
        
    def test_upload_image_form(self):
        self.assertEqual(Image.objects.count(), 0)
        file = DjangoFile(open(self.filename), name=self.image_name)
        upoad_image_form = UploadImageFileForm({'original_filename':self.image_name,
                                                'owner': self.superuser.pk},
                                                {'file':file})
        if upoad_image_form.is_valid():
            image = upoad_image_form.save()
            self.assertEqual(Image.objects.count(), 1)              
        
    def test_create_clipboard_item(self):
        image = self.create_filer_image()
        image.save()
        # Get the clipboard of the current user
        clipboard_item = create_clipboard_item(user=self.superuser,
                              file=image)
        clipboard_item.save()
        self.assertEqual(Clipboard.objects.count(), 1)
        
    def test_create_icons(self):
        image = self.create_filer_image()
        image.save()
        icons = image.icons
        file_basename = os.path.basename(image.file.path)
        self.assertEqual(len(icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        for size in filer_settings.FILER_ADMIN_ICON_SIZES:
            self.assertEqual(os.path.basename(icons[size]),
                             file_basename + u'.%sx%s_q85_crop_upscale.jpg' %(size,size))
         
        
    def test_file_upload_public_destination(self):
        """
        Test where an image `is_public` == True is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_ROOT))
        
    def test_file_upload_private_destination(self):
        """
        Test where an image `is_public` == False is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_ROOT))
        
    def test_file_move_location(self):
        """
        Test the method that move a file between filer_public, filer_private
        and vice et versa
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_ROOT))
        image._move_file(filer_settings.FILER_PRIVATEMEDIA_PREFIX,
                        filer_settings.FILER_PUBLICMEDIA_PREFIX)
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_ROOT))
        
        
        
        
    def test_file_change_upload_to_destination(self):
        """
        Test that the file is actualy move from the private to the public
        directory when the is_public is checked on an existing private file.
        """
        file = DjangoFile(open(self.filename), name=self.image_name)
        
        image = Image.objects.create(owner=self.superuser,
                                     is_public=False,
                                     original_filename=self.image_name,
                                     file=file)
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_ROOT))
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_ROOT))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_ROOT))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        