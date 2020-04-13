#-*- coding: utf-8 -*-
from django.conf.urls import url

urlpatterns = ['filer.server.views',
    url(r'^(?P<path>.*)$', 'serve_protected_file',)
]
