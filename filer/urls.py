from django.urls import re_path

from . import settings as filer_settings
from . import views

urlpatterns = [
    re_path(
        filer_settings.FILER_CANONICAL_URL + r'(?P<uploaded_at>[0-9]+)/(?P<file_id>[0-9]+)/$',
        views.canonical,
        name='canonical'
    ),
    re_path(
        filer_settings.FILER_CANONICAL_URL
        + r"(?P<slug>[\-\.\w]+)/?$",  # flake8: noqa
        views.canonical_slug,
        name="canonical",
    ),
]
