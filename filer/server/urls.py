#-*- coding: utf-8 -*-
from django.conf.urls import url, include
from filer import settings as filer_settings

if not filer_settings.FILER_0_8_COMPATIBILITY_MODE:
    urlpatterns = ['filer.server.views',
        url(r'^' + filer_settings.FILER_PRIVATEMEDIA_STORAGE.base_url.lstrip('/'), include('filer.server.main_server_urls')),
        url(r'^' + filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.base_url.lstrip('/'), include('filer.server.thumbnails_server_urls'))
    ]
else:
    urlpatterns = urlpatterns('')