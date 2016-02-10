#-*- coding: utf-8 -*-

import json
from lxml import html
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File as DjangoFile
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

from filer import settings as filer_settings
from filer.models import File, Folder, Image
from filer.tests.helpers import create_superuser, create_image
from filer.utils.folders import DefaultFolderGetter, get_default_folder_getter
from filer.validators import FileMimetypeValidator, validate_documents, validate_images
from filer.test_utils.thirdparty_app.models import Example


class FilerTestMixin(object):
    def setUp(self):
        super(FilerTestMixin, self).setUp()
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, 'JPEG')
        self.usersfolder, self.usersfolder_created = Folder.objects.get_or_create(
            name='users_files', parent=None, defaults={'owner': self.superuser,})

    def tearDown(self):
        File.objects.all().delete()
        if self.usersfolder_created:
            self.usersfolder.delete()
        self.client.logout()


class FilerDynamicFolderTest(FilerTestMixin, TestCase):

    def test_filer_dynamic_folder_creation(self):
        rf = RequestFactory()
        request = rf.get("/")
        request.session = {}
        request.user = self.superuser
        folder = get_default_folder_getter().get('USER_OWN_FOLDER', request)
        self.assertEqual(folder.name, self.superuser.username)

    def test_filer_dynamic_folder_ajax_upload_file(self):
        self.assertEqual(Image.objects.count(), 0)
        file_obj = DjangoFile(open(self.filename, 'rb'))

        url = reverse('admin:filer-ajax_upload', kwargs={'folder_key': 'USER_OWN_FOLDER'})
        url += '?qqfile=%s' % (self.image_name, )
        response = self.client.post(
            url, data=file_obj.read(), content_type='application/octet-stream',
            **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        )
        self.assertEqual(Image.objects.count(), 1)
        img = Image.objects.all()[0]
        self.assertEqual(img.original_filename, self.image_name)
        self.assertEqual(img.folder.name, self.superuser.username)
        self.assertEqual(img.folder.parent_id, self.usersfolder.pk)


class FilerMimetypeLimitationTest(FilerTestMixin, TestCase):

    def setUp(self):
        super(FilerMimetypeLimitationTest, self).setUp()
        file_obj = DjangoFile(open(self.filename, 'rb'), name=self.image_name)
        self.image = Image.objects.create(
            owner=self.superuser,
            is_public=True,
            original_filename=self.image_name,
            file=file_obj
        )

    def test_filer_specific_mimetype_validator(self):
        jpeg_validator = FileMimetypeValidator(['image/jpeg',])
        try:
            jpeg_validator(self.image.pk)
        except ValidationError:
            self.failfast("FileMimetypeValidator() raised ValidationError unexpectedly !")

        png_validator = FileMimetypeValidator(['image/png',])
        with self.assertRaises(ValidationError):
            png_validator(self.image.pk)

    def test_filer_generic_mimetype_validator(self):
        try:
            validate_images(self.image.pk)
        except ValidationError:
            self.failfast("FileMimetypeValidator() raised ValidationError unexpectedly !")

        with self.assertRaises(ValidationError):
            validate_documents(self.image.pk)

    def test_filer_partial_ajax_upload_mimetype_validator(self):
        self.assertEqual(File.objects.count(), 1)
        file_obj = DjangoFile(open(self.filename, 'rb'))
        url = reverse('admin:filer-ajax_upload',
                      kwargs={'related_field': 'thirdparty_app.Example.illustration_browse_only',
                              'folder_key': 'no_folder'})
        url += '?qqfile=other.jpeg'
        response = self.client.post(
            url, data=file_obj.read(), content_type='application/octet-stream',
            **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(File.objects.count(), 2)
        self.assertEqual(Image.objects.count(), 2)

        file_obj.seek(0)

        url = reverse('admin:filer-ajax_upload',
                      kwargs={'related_field': 'thirdparty_app.Example.document_choose_or_browse',
                              'folder_key': 'no_folder'})
        url += '?qqfile=again.jpeg'
        response = self.client.post(
            url, data=file_obj.read(), content_type='application/octet-stream',
            **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(File.objects.count(), 2)
        data = json.loads(response.content.decode())
        self.assertTrue(bool(data.get('error')))


class FilerWidgetTest(FilerTestMixin, TestCase):

    def test_filer_widget_choose_and_or_browse(self):
        url = reverse('admin:thirdparty_app_example_add')
        response = self.client.get(url)
        dom = html.fromstring(response.content)
        ids = [
            el.attrib['id'] for el in dom.xpath('//a[@class="js-related-lookup related-lookup"]')]
        expected_choose_ids = [
            'id_file_choose_only_lookup', 'id_document_choose_or_browse_lookup']
        self.assertEqual(ids, expected_choose_ids)

        ids = [
            el.attrib['id'] for el in dom.xpath('//div[@class="dz-default dz-message '\
                                                'js-filer-dropzone-message"]')]
        expected_browse_ids = [
            'id_illustration_browse_only_filer_dropzone_message',
            'id_document_choose_or_browse_filer_dropzone_message']
        self.assertEqual(ids, expected_browse_ids)


    def test_filer_widget_folder_key(self):
        url = reverse('admin:thirdparty_app_example_add')
        response = self.client.get(url)
        dom = html.fromstring(response.content)

        for field_name in ('file_choose_only', 'document_choose_or_browse'):
            field = Example._meta.get_field_by_name(field_name)[0]
            folder_key = field.default_formfield_kwargs.get('folder_key')
            expected_href = reverse(
                'admin:filer-directory_listing_by_key', kwargs={'folder_key':folder_key})
            try:
                href = dom.get_element_by_id('id_%s_lookup' % field_name).attrib['href']
            except (KeyError, IndexError):
                self.fail('DOM for "%s" field is not as expected.' % field_name)[0]
            href = href.split('?')[0]
            self.assertEqual(href, expected_href)