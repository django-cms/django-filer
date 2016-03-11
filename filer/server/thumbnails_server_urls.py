# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf.urls import patterns, url

urlpatterns = patterns('filer.server.views',
    url(r'^(?P<path>.*)$', 'serve_protected_thumbnail',),
)
