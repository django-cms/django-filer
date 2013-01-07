#-*- coding: utf-8 -*-
try:
    # django >=1.4
    from django.conf.urls import patterns, url
except ImportError:
    # django <1.4
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('filer.server.views',
    url(r'^(?P<path>.*)$', 'serve_protected_thumbnail',),
)
