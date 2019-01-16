# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
from zipfile import ZipFile

from django.conf import settings
from django.core.files import File as DjangoFile
from django.test.testcases import TestCase

from ..utils.loader import load_object as load
from ..utils.zip import unzip
from .helpers import create_image


#===============================================================================
# Some target classes for the classloading tests
#===============================================================================
class TestTargetSuperClass(object):
    pass


class TestTargetClass(TestTargetSuperClass):
    pass


#===============================================================================
# Testing the classloader
#===============================================================================
class ClassLoaderTestCase(TestCase):
    ''' Tests filer.utils.loader.load() '''

    def test_loader_loads_strings_properly(self):
        target = 'filer.tests.utils.TestTargetClass'
        result = load(target, None) # Should return an instance
        self.assertEqual(result.__class__, TestTargetClass)

    def test_loader_loads_class(self):
        result = load(TestTargetClass(), TestTargetSuperClass)
        self.assertEqual(result.__class__, TestTargetClass)

    def test_loader_loads_subclass(self):
        result = load(TestTargetClass, TestTargetSuperClass)
        self.assertEqual(result.__class__, TestTargetClass)


#===============================================================================
# Testing the zipping/unzipping of files
#===============================================================================
class ZippingTestCase(TestCase):

    def setUp(self):
        self.img = create_image()
        self.image_name = 'test_file.jpg'
        self.filename = os.path.join(settings.FILE_UPLOAD_TEMP_DIR, self.image_name)
        self.img.save(self.filename, 'JPEG')

        self.file = DjangoFile(open(self.filename, 'rb'), name=self.image_name)

        self.zipfilename = 'test_zip.zip'

        self.zip = ZipFile(self.zipfilename, 'a')
        self.zip.write(self.filename)
        self.zip.close()

    def tearDown(self):
        # Clean up the created zip file
        os.remove(self.zipfilename)
        os.remove(self.filename)

    def test_unzipping_works(self):
        result = unzip(self.zipfilename)
        self.assertEqual(result[0][0].name, self.file.name)
