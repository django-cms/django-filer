"""
URLs used by the end-to-end tests.

Django forces ``DEBUG = False`` while tests run, so ``static()`` in
``demoapp.urls`` never contributes the media route. The browser however does
need to load thumbnails, hence media files are served unconditionally here.
"""

from django.conf import settings
from django.urls import re_path
from django.views.static import serve

from demoapp.urls import urlpatterns as demoapp_urlpatterns


urlpatterns = demoapp_urlpatterns + [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
