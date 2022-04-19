from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.views.decorators.cache import never_cache

from easy_thumbnails.files import ThumbnailFile

from .. import settings as filer_settings
from ..models import File
from ..utils.filer_easy_thumbnails import thumbnail_to_original_filename


server = filer_settings.FILER_PRIVATEMEDIA_SERVER
thumbnail_server = filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_SERVER


@never_cache
def serve_protected_file(request, path):
    """
    Serve protected files to authenticated users with read permissions.
    """
    try:
        file_obj = File.objects.get(file=path, is_public=False)
    except File.DoesNotExist:
        raise Http404('File not found')
    if not file_obj.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    return server.serve(request, file_obj, save_as=False)


@never_cache
def serve_protected_thumbnail(request, path):
    """
    Serve protected thumbnails to authenticated users.
    If the user doesn't have read permissions, redirect to a static image.
    """
    source_path = thumbnail_to_original_filename(path)
    if not source_path:
        raise Http404('File not found')
    try:
        file_obj = File.objects.get(file=source_path, is_public=False)
    except File.DoesNotExist:
        raise Http404('File not found')
    if not file_obj.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    try:
        thumbnail = ThumbnailFile(name=path, storage=file_obj.file.thumbnail_storage)
        thumbnail.mime_type = file_obj.mime_type
        return thumbnail_server.serve(request, thumbnail, save_as=False)
    except Exception:
        raise Http404('File not found')
