#-*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url, include
from filer import settings as filer_settings

if not filer_settings.FILER_0_8_COMPATIBILITY_MODE:
    urlpatterns = patterns('filer.server.views',
        url(r'^' + filer_settings.FILER_PRIVATEMEDIA_STORAGE.base_url.lstrip('/'), include('filer.server.main_server_urls')),
        url(r'^' + filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.base_url.lstrip('/'), include('filer.server.thumbnails_server_urls')),
    )
else:
    urlpatterns = patterns('')