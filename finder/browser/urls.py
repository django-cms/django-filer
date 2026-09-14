from django.urls import NoReverseMatch, path, reverse
from django.views.i18n import JavaScriptCatalog

from finder.browser.views import BrowserView


app_name = 'finder-api'
urlpatterns = [
    path(
        'structure/<slug:slug>',
        BrowserView.as_view(action='structure'),
    ),
    path(
        '<uuid:inode_id>/fetch',
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
        '<uuid:image_id>/crop',
        BrowserView.as_view(action='crop'),
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


def reverse_api(viewname):
    """
    Reverse one of the endpoints above.

    The admin serves them below ``finder-api/`` (see ``finder.admin.ambit.get_urls``), but
    a project may additionally include this module in its own URLconf. That mount is
    preferred here, because it is the explicit one and it does not live below ``admin/``.
    """
    try:
        return reverse(f'finder-api:{viewname}')
    except NoReverseMatch:
        return reverse(f'admin:finder-api:{viewname}')
