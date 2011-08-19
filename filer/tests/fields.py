# -*- coding: utf-8 -*-
from django.core.exceptions import ImproperlyConfigured
from django.test.testcases import TestCase
from filer.fields.image import FilerImageField

class FieldsTests(TestCase):
    def test_related_name_validation(self):
        self.assertRaises(ImproperlyConfigured, FilerImageField, related_name='thumbnails')
        FilerImageField(related_name='not_thumbnails')
