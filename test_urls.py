#-*- coding: utf-8 -*-
try:
    # django >=1.4
    from django.conf.urls import patterns, url, include
except ImportError:
    # django <1.4
    from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('filer.server.urls')),
)