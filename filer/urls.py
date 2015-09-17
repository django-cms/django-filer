#-*- coding: utf-8 -*-
from django.conf.urls import url

from filer import views

urlpatterns = [
    url(r'canonical/(?P<uploaded_at>[0-9]+)/(?P<file_id>[0-9]+)/$', views.canonical, name='canonical'),
]
