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
        '<uuid:folder_id>/fetch',
        BrowserView.as_view(action='fetch'),
    ),
    path(
        '<uuid:folder_id>/open',
        BrowserView.as_view(action='open'),
    ),
    path(
        '<uuid:folder_id>/close',
        BrowserView.as_view(action='close'),
    ),
    path(
        '<uuid:folder_id>/list',
        BrowserView.as_view(action='list'),
    ),
    path(
        '<uuid:folder_id>/search',
        BrowserView.as_view(action='search'),
    ),
    path(
        '<uuid:folder_id>/upload',
        BrowserView.as_view(action='upload'),
    ),
    path(
        '<uuid:file_id>/change',
        BrowserView.as_view(action='change'),
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
