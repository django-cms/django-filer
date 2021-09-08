#-*- coding: utf-8 -*-
from django.urls import re_path, include
from filer import settings as filer_settings

urlpatterns = [
    re_path(r'^' + filer_settings.FILER_PRIVATEMEDIA_STORAGE.base_url.lstrip('/'), include('filer.server.main_server_urls')),
    re_path(r'^' + filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE.base_url.lstrip('/'), include('filer.server.thumbnails_server_urls'))
]
