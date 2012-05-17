#-*- coding: utf-8 -*-
from django.test import TestCase
import filer


class GeneralTestCase(TestCase):
    def test_version_is_set(self):
        self.assertTrue(len(filer.get_version())>0)