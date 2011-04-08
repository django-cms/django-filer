#-*- coding: utf-8 -*-
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import Http404
from easy_thumbnails.files import ThumbnailFile
from filer import settings as filer_settings
from filer.models import File
from filer.server.backends.base import ServerBase
from filer.utils.filer_easy_thumbnails import thumbnail_to_original_filename
from filer.utils.loader import load
server = load(filer_settings.FILER_PRIVATEMEDIA_SERVER, ServerBase)

def serve_protected_file(request, path):
    """
    Serve protected files to authenticated users with read permissions.
    """
    thefile = File.objects.get(file=path)
    if thefile == None:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    return server.serve(request, file=thefile.file, save_as=False)

def serve_protected_thumbnail(request, path):
    """
    Serve protected thumbnails to authenticated users.
    If the user doesn't have read permissions, redirect to a static image.
    """
    source_path = thumbnail_to_original_filename(path)
    if not source_path:
        raise Http404('File not found')
    thefile = File.objects.get(file=source_path)
    if thefile == None:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    try:
        thumbnail = ThumbnailFile(name="thumbs/" + path, storage=thefile.file.thumbnail_storage)
        return server.serve(request, thumbnail, save_as=False)
    except Exception, e:
        raise Http404('File not found')

