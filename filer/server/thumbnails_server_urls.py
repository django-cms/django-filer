#-*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('filer.server.views',
    url(r'^(?P<path>.*)$', 'serve_protected_thumbnail',),
)
