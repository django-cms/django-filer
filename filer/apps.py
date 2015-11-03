# -*- coding: utf-8 -*-

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FilerConfig(AppConfig):
    name = 'filer'
    verbose_name = _("django filer")
