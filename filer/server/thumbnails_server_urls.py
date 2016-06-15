# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf.urls import url

urlpatterns = [
    url(r'^(?P<path>.*)$', 'filer.server.views.serve_protected_thumbnail',),
]
