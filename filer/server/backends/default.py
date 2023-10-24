import os
import stat

from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.utils.http import http_date
from django.views.static import was_modified_since

from .base import ServerBase


class DefaultServer(ServerBase):
    """
    Serve static files from the local filesystem through django.
    This is a bad idea for most situations other than testing.

    This will only work for files that can be accessed in the local filesystem.
    """
    def serve(self, request, filer_file, **kwargs):
        fullpath = filer_file.path
        # the following code is largely borrowed from `django.views.static.serve`
        # and django-filetransfers: filetransfers.backends.default
        if not os.path.exists(fullpath):
            raise Http404('"%s" does not exist' % fullpath)
        # Respect the If-Modified-Since header.
        statobj = os.stat(fullpath)
        response_params = {'content_type': filer_file.mime_type}
        if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'),
                                  statobj[stat.ST_MTIME]):
            return HttpResponseNotModified(**response_params)
        response = HttpResponse(open(fullpath, 'rb').read(), **response_params)
        response["Last-Modified"] = http_date(statobj[stat.ST_MTIME])
        self.default_headers(request=request, response=response, file_obj=filer_file.file, **kwargs)
        return response
