#-*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import os, tempfile, json

from django.conf import settings
from django.core.files import File as DjangoFile
from django.core.management import call_command
from django.test import TestCase

from ..models.filemodels import File
from ..models.imagemodels import Image
from .helpers import create_image, create_superuser

try:
    from unittest import skipIf, skipUnless
except ImportError:
    # Django<1.9
    from django.utils.unittest import skipIf, skipUnless


class FixtureLoadingTests(TestCase):
    def setUp(self):
        self.superuser = create_superuser()
        self.client.login(username='admin', password='secret')
        img = create_image()
        image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, image_name)
        img.save(self.filename, 'JPEG')
        file_obj = DjangoFile(open(self.filename, 'rb'), name=image_name)
        self.image = Image.objects.create(owner=self.superuser, original_filename=image_name, file=file_obj)

    def tearDown(self):
        self.client.logout()
        os.remove(self.filename)
        for f in File.objects.all():
            f.delete()

    def dump_and_reimport_fixture(self):
        with tempfile.NamedTemporaryFile() as fixture:
            call_command('dumpdata', 'filer', output=fixture.name,
                         exclude=['filer.clipboard', 'filer.clipboarditem'])
            fixture.seek(0)
            data = json.load(fixture)[0]
            self.assertEqual(data['pk'], self.image.pk)
            self.assertEqual(data['model'], 'filer.image')
            data['fields'].pop('date_taken')
            self.assertDictContainsSubset({
                'subject_location': self.image.subject_location,
                'must_always_publish_copyright': self.image.must_always_publish_copyright,
                'author': self.image.author,
                '_height': self.image._height,
                '_width': self.image._width,
                'must_always_publish_author_credit': self.image.must_always_publish_author_credit,
                'default_alt_text': self.image.default_alt_text,
                'default_caption': self.image.default_caption,
            }, data['fields'])
