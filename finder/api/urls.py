from django.urls import path
from django.views.i18n import JavaScriptCatalog

from finder.api.views import BrowserView


app_name = 'finder-api'
urlpatterns = [
    path(
        'structure/<slug:realm>',
        BrowserView.as_view(action='structure'),
    ),
    path(
        'fetch/<uuid:folder_id>',
        BrowserView.as_view(action='fetch'),
    ),
    path(
        'open/<uuid:folder_id>',
        BrowserView.as_view(action='open'),
    ),
    path(
        'close/<uuid:folder_id>',
        BrowserView.as_view(action='close'),
    ),
    path(
        'list/<uuid:folder_id>',
        BrowserView.as_view(action='list'),
    ),
    path(
        'jsi18n/',
        JavaScriptCatalog.as_view(packages=['finder']),
        name="javascript-catalog",
    ),
    path(
        '',
        BrowserView.as_view(),
        name="base-url",
    ),
]
