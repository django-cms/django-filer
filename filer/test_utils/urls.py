# -*- coding: utf-8 -*-

from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve',  # NOQA
        {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('filer.server.urls')),
    url(r'^filer/', include('filer.urls')),
]
