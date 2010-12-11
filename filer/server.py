
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.conf import settings as django_settings
import posixpath
import settings

class UnprotectedServer:
    def serve(self, request, url, media_path, full_path, size):
        return HttpResponseRedirect(url)

    def direct_access(self, request, filer_path):
        from django.views.static import serve
        return serve(request, path=filer_path, document_root=settings.FILER_PRIVATEMEDIA_ROOT)

class ApacheXSendfileServer:
    def serve(self, request, url, media_path, full_path, size):
        response = HttpResponse()
        response['X-Sendfile'] = full_path
        response['Content-Length'] = size
        del response['Content-Type'] # let Apache decide
        #response['Content-Disposition'] = 'attachment; filename="%s"' % posixpath.basename(full_path)
        return response

    def direct_access(self, request, filer_path):
        newpath = posixpath.join(settings.FILER_STATICMEDIA_PREFIX, "icons/missingfile_32x32.png")
        return HttpResponseRedirect(newpath)

class DjangoStaticServer:
    def serve(self, request, url, media_path, full_path, size):
        #url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
        #    {'document_root': settings.MEDIA_ROOT, 'show_indexes': True})
        from django.views.static import serve
        return serve(request, path=media_path, document_root=django_settings.MEDIA_ROOT)

    def direct_access(self, request, filer_path):
        newpath = posixpath.join(settings.FILER_STATICMEDIA_PREFIX, "icons/missingfile_32x32.png")
        return HttpResponseRedirect(newpath)
