from django.test import TestCase

from filer.tests.admin import *
from filer.tests.models import *

class FilerTests(TestCase):
    def test_environment(self):
        """Just make sure everything is set up correctly."""
        self.assert_(True)
        
