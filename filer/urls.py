from django.urls import path

from . import settings as filer_settings
from . import views


urlpatterns = [
    path(
        filer_settings.FILER_CANONICAL_URL + '<int:uploaded_at>/<int:file_id>/',
        views.canonical,
        name='canonical'
    ),
]
