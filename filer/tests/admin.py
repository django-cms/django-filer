import os
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.files import File as DjangoFile

from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.tests.helpers import (create_superuser, create_folder_structure,
                                 create_image)


class FilerFolderAdminUrlsTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
    def tearDown(self):
        self.client.logout()
    def test_filer_app_index_get(self):
        response = self.client.get(reverse('admin:app_list', args=('filer',)))
        self.assertEqual(response.status_code, 200)

    def test_filer_make_root_folder_get(self):
        response = self.client.get(reverse('admin:filer-directory_listing-make_root_folder'))
        self.assertEqual(response.status_code, 200)
        
    def test_filer_make_root_folder_post(self):
        FOLDER_NAME = "root folder 1"
        self.assertEqual(Folder.objects.count(), 0)
        response = self.client.post(reverse('admin:filer-directory_listing-make_root_folder'),
                                    {
                                        "name":FOLDER_NAME,
                                    })
        self.assertEqual(Folder.objects.count(), 1)
        self.assertEqual(Folder.objects.all()[0].name, FOLDER_NAME)
        #TODO: not sure why the status code is 200
        self.assertEqual(response.status_code, 200)
        
    def test_filer_directory_listing_root_empty_get(self):
        response = self.client.post(reverse('admin:filer-directory_listing-root'))
        self.assertEqual(response.status_code, 200)
        
    def test_filer_directory_listing_root_get(self):
        create_folder_structure(depth=3, sibling=2, parent=None)
        response = self.client.post(reverse('admin:filer-directory_listing-root'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['folder'].children.count(), 6)
        
    
class FilerImageAdminUrlsTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        
    def tearDown(self):
        self.client.logout()
        
    #def test_filer_image_move_to_folder(self):
    #    self.assertTrue(False)
        
        
class FilerClipboardAdminUrlsTests(TestCase):
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
        
    def test_filer_upload_file(self):
        self.assertEqual(Image.objects.count(), 0)
        file = DjangoFile(open(self.filename))
        response = self.client.post(reverse('admin:filer-ajax_upload'),
                                    {
                                       'Filename':self.image_name, 
                                        'Filedata': file,
                                       'jsessionid':self.client.session.session_key,
                                    })
        self.assertEqual(Image.objects.count(), 1)
        self.assertEqual(Image.objects.all()[0].original_filename,
                         self.image_name)
        
        
    #def test_filer_paste_clipboard_to_folder(self):
    #    self.assertTrue(False)
    #    
    #def test_filer_discard_clipboard(self):
    #    self.assertTrue(False)
        