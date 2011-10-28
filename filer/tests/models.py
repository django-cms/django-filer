#-*- coding: utf-8 -*-
import os
from django.forms.models import modelform_factory
from django.test import TestCase
from django.core.files import File as DjangoFile

from filer.models.foldermodels import Folder
from filer.models.imagemodels import Image
from filer.models.videomodels import Video
from filer.models.clipboardmodels import Clipboard
from filer.tests.helpers import (create_superuser, create_folder_structure,
                                 create_image, create_clipboard_item)
from filer import settings as filer_settings
from filer.utils.video import check_ffmpeg_available


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
        ImageUploadForm = modelform_factory(Image, fields=('original_filename', 'owner', 'file'))
        upoad_image_form = ImageUploadForm({'original_filename':self.image_name,
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
                             file_basename + u'__%sx%s_q85_crop_upscale.jpg' %(size,size))

    def test_file_upload_public_destination(self):
        """
        Test where an image `is_public` == True is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))

    def test_file_upload_private_destination(self):
        """
        Test where an image `is_public` == False is uploaded.
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))

    def test_file_move_location(self):
        """
        Test the method that move a file between filer_public, filer_private
        and vice et versa
        """
        image = self.create_filer_image()
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))

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
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        image.is_public = True
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PUBLICMEDIA_STORAGE.location))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))
        image.is_public = False
        image.save()
        self.assertTrue(image.file.path.startswith(filer_settings.FILER_PRIVATEMEDIA_STORAGE.location))
        self.assertEqual(len(image.icons), len(filer_settings.FILER_ADMIN_ICON_SIZES))



class FilerVideoApiTest(TestCase):
    
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.video_name = 'video_test.mp4'
        self.video_path = os.path.join(os.path.dirname(__file__), 'mediafiles', self.video_name)
        self.is_ffmpeg_available = check_ffmpeg_available()
        
    def tearDown(self):
        self.client.logout()
        for video in Video.objects.all():
            self.delete_filer_video(video)

    def delete_filer_video(self, video):
        for entry in video.formats:
            os.remove(entry['filepath'])
        if video.poster.has_key('filepath') and video.poster['filepath']:
            os.remove(video.poster['filepath'])
        video.delete()

    def create_filer_video(self):
        djfile = DjangoFile(open(self.video_path), name=self.video_name)
        video = Video.objects.create(owner=self.superuser,
                                     original_filename=self.video_name,
                                     file=djfile)
        return video
        
    def test_create_and_delete_video(self):
        self.assertEqual(Video.objects.count(), 0)
        video = self.create_filer_video()
        video.save()
        self.assertEqual(video.conversion_status, 'new')
        self.assertEqual(Video.objects.count(), 1)
        video = Video.objects.all()[0]
        self.delete_filer_video(video)
        self.assertEqual(Video.objects.count(), 0)
    
    def test_upload_video_form(self):
        self.assertEqual(Video.objects.count(), 0)
        djfile = DjangoFile(open(self.video_path), name=self.video_name)
        VideoUploadForm = modelform_factory(Video, fields=('original_filename', 'owner', 'file'))
        upoad_video_form = VideoUploadForm({'original_filename':self.video_name,
                                                'owner': self.superuser.pk},
                                                {'file':djfile})
        if upoad_video_form.is_valid():
            video = upoad_video_form.save()
        self.assertEqual(Video.objects.count(), 1)
        self.assertEqual(video.conversion_status, 'new')
        self.delete_filer_video(video)
    
    def test_convert_video(self):
        if not self.is_ffmpeg_available:
            return
        self.assertEqual(Video.objects.count(), 0)
        video = self.create_filer_video()
        video.save()
        self.assertEqual(Video.objects.count(), 1)
        self.assertEqual(video.width, 320)
        self.assertEqual(video.height, 240)
        old_setting = filer_settings.FILER_VIDEO_FORMATS
        filer_settings.FILER_VIDEO_FORMATS = ('flv', 'mp4', 'webm')
        video.convert()
        self.assertEqual(video.original_format()['url'].endswith('video_test.mp4'), True)
        formats = [ entry['format'] for entry in video.formats ]
        self.assertEqual('webm' in formats, True)
        self.assertEqual('flv' in formats, True)
        self.assertNotEqual(video.format_flash(), None)
        self.assertEqual(video.poster['url'].endswith('png'), True)
        video = Video.objects.all()[0]
        self.delete_filer_video(video)
        self.assertEqual(Video.objects.count(), 0)
        filer_settings.FILER_VIDEO_FORMATS = old_setting