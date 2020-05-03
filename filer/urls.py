# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import url

from . import settings as filer_settings
from . import views


urlpatterns = [
    url(
        filer_settings.FILER_CANONICAL_URL + r'(?P<uploaded_at>[0-9]+)/(?P<file_id>[0-9]+)/$',  # flake8: noqa
        views.canonical,
        name='canonical'
    ),
]
