# -*- coding: utf-8 -*-

try:
    from django.utils import unittest as djut
except ImportError:
    djut = None
import unittest as stdut

if hasattr(stdut, 'skipIf'):
    skipIf = stdut.skipIf
    skipUnless = stdut.skipUnless
elif hasattr(djut, 'skipIf'):
    skipIf = djut.skipIf
    skipUnless = djut.skipUnless