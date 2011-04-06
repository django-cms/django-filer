#-*- coding: utf-8 -*-
from django.test.testcases import TestCase
from filer.utils.loader import load

#===============================================================================
# Some target classes for the classloading tests
#===============================================================================
class TestTargetSuperClass(object):
    pass

class TestTargetClass(TestTargetSuperClass):
    pass

#===============================================================================
# The actual test code
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