# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^(?P<path>.*)$', views.serve_protected_file),
]
