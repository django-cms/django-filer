#-*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from filer import settings as filer_settings

urlpatterns = patterns('filer.server.views',
    url(r'^' + filer_settings.FILER_PRIVATEMEDIA_STORAGE.base_url.lstrip('/') + r'(?P<path>.*)$',
        'serve_protected_file',),

    url(r'^' + filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.base_url.lstrip('/') + r'(?P<path>.*)$',
        'serve_protected_thumbnail',),
)
