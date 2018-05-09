# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

from django.conf import settings

__all__ = ['CMS_IS_INSTALLED', 'PARLER_IS_INSTALLED']


PARLER_IS_INSTALLED = 'parler' in settings.INSTALLED_APPS
CMS_IS_INSTALLED = 'cms' in settings.INSTALLED_APPS
