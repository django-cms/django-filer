import os
import mimetypes
import stat
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponseNotModified
from django.utils.http import http_date
from django.utils.encoding import smart_str
from django.views.static import was_modified_since
from filer.server.backends.base import ServerBase

class DefaultServer(ServerBase):
    '''
    Serve static files from the local filesystem through django.
    This is a bad idea for situations other than testing.
    
    This will only work for files in the local filesystem.
    '''
    def serve(self, request, file, **kwargs):
        fullpath = file.path
        # the following code is largely borrowed from `django.views.static.serve`
        # and django-filetransfers: filetransfers.backends.default
        if not os.path.exists(fullpath):
            raise Http404('"%s" does not exist' % fullpath)
        # Respect the If-Modified-Since header.
        statobj = os.stat(fullpath)
        mimetype = mimetypes.guess_type(fullpath)[0] or 'application/octet-stream'
        if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
                                  statobj[stat.ST_MTIME], statobj[stat.ST_SIZE]):
            return HttpResponseNotModified(mimetype=mimetype)
        response = HttpResponse(open(fullpath, 'rb').read(), mimetype=mimetype)
        response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
        self.default_headers(request, response, file=file, **kwargs)
        return response
