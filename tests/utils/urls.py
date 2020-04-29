# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.static import serve


admin.autodiscover()
admin_urls = admin.site.urls

urlpatterns = [
    url(r'^media/(?P<path>.*)$', serve,
        {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    url(r'^admin/', admin_urls),
    url(r'^', include('filer.server.urls')),
    url(r'^filer/', include('filer.urls')),
]
