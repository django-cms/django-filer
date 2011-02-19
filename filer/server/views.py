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

@login_required
def serve_protected_thumbnail(request, path):
    """
    Serve protected thumbnails to authenticated users.
    If the user doesn't have read permissions, redirect to a static image.
    """
    source_path = path[:-37]
    print 'path', path
    print 'source_path', source_path
    thefile = File.objects.get(file=source_path)
    print thefile
    if thefile == None:
        raise Http404('File not found')
    if not thefile.has_read_permission(request):
        print "NOREAD"
        if settings.DEBUG:
            raise PermissionDenied
        else:
            raise Http404('File not found')
    try:
        thumbnail = ThumbnailFile(name="_/" + path, storage=thefile.file.thumbnail_storage)
        print server
        return server.serve(request, thumbnail, save_as=False)
    except Exception, e:
        raise Http404('File not found')

