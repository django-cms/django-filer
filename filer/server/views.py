from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseServerError
from django.core.exceptions import PermissionDenied
from django.conf import settings
from easy_thumbnails.files import ThumbnailFile
from filer.models import File
from filer.utils.loader import load
from filer import settings as filer_settings
from filer.server.backends.base import ServerBase
server = load(filer_settings.FILER_PRIVATEMEDIA_SERVER, ServerBase)

@login_required
def serve_protected_file(request, file_id, file_name):
    """
    Serve protected files to authenticated users with read permissions.
    """
    thefile = File.objects.get(id=file_id)
    if thefile == None:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    return server.serve(request, file=thefile.file)

@login_required
def serve_protected_thumbnail(request, file_id, file_name):
    """
    Serve protected thumbnails to authenticated users.
    If the user doesn't have read permissions, redirect to a static image.
    """
    thefile = File.objects.get(id=file_id)
    if thefile == None:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    try:
        # we don't care about the options because they're in file_name
        # so we just pass the required size option
        #name = thefile.file.get_thumbnail_name(thumbnail_options = { 'size': (1,1)})
        file_name = 'thumbnails/' + file_name.rstrip('/')
        thumbnail = ThumbnailFile(name=file_name, storage=thefile.file.thumbnail_storage)
        return server.serve(request, thumbnail)
    except Exception, e:
        raise Http404('File not found')

