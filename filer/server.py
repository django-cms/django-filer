
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.conf import settings as django_settings
import posixpath
import settings

class ServerBase:
    def __init__(self):
        self._allowDirectAccess = False

    @property
    def allowsDirectAccess(self):
        return self._allowDirectAccess

# UnprotectedServer.serve() redirects all authenticated requests by-id to
# direct_url. The redirected url is then handled by direct_access() which uses
# django.views.static.serve to serve the files.
#
# Requests by-id that are not authenticated are blocked in serve_protected_*
# views, but the files are still accessible with direc urls (direct_file_access
# view)
class UnprotectedServer(ServerBase):
    def __init__(self):
        self._allowDirectAccess = True

    # Params:
    #   direct_url - the url to access the file directly 
    #   media_path - path relative to MEDIA_ROOT
    #   filer_path - path relative to FILER_PRIVATEMEDIA_ROOT
    # size - file size
    def serve(self, request, direct_url, media_path, full_path, size):
        return HttpResponseRedirect(direct_url)

    #def direct_access(self, request, filer_path):
    #    from django.views.static import serve
    #    return serve(request, path=filer_path, document_root=settings.FILER_PRIVATEMEDIA_ROOT)

class ApacheXSendfileServer(ServerBase):
    def serve(self, request, direct_url, media_path, full_path, size):
        response = HttpResponse()
        response['X-Sendfile'] = full_path
        response['Content-Length'] = size
        del response['Content-Type'] # let Apache decide
        #response['Content-Disposition'] = 'attachment; filename="%s"' % posixpath.basename(full_path)
        return response

    def direct_access(self, request, filer_path):
        newpath = posixpath.join(settings.FILER_STATICMEDIA_PREFIX, "icons/missingfile_32x32.png")
        return HttpResponseRedirect(newpath)

class DjangoStaticServer(ServerBase):
    def serve(self, request, direct_url, media_path, full_path, size):
        #url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
        #    {'document_root': settings.MEDIA_ROOT, 'show_indexes': True})
        from django.views.static import serve
        return serve(request, path=media_path, document_root=django_settings.MEDIA_ROOT)

    def direct_access(self, request, filer_path):
        newpath = posixpath.join(settings.FILER_STATICMEDIA_PREFIX, "icons/missingfile_32x32.png")
        return HttpResponseRedirect(newpath)

