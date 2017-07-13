# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from django.conf import settings


__all__ = ['CMS_IS_INSTALLED', 'PARLER_IS_INSTALLED']


PARLER_IS_INSTALLED = 'parler' in settings.INSTALLED_APPS
CMS_IS_INSTALLED = 'cms' in settings.INSTALLED_APPS
