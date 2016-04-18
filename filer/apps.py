# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FilerConfig(AppConfig):
    name = 'filer'
    verbose_name = _("Filer")
