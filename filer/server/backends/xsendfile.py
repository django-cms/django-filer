from django.http import HttpResponse

from .base import ServerBase


class ApacheXSendfileServer(ServerBase):
    def serve(self, request, filer_file, **kwargs):
        response = HttpResponse()
        response['X-Sendfile'] = filer_file.path

        # This is needed for lighttpd, hopefully this will
        # not be needed after this is fixed:
        # http://redmine.lighttpd.net/issues/2076
        response['Content-Type'] = filer_file.mime_type

        self.default_headers(request=request, response=response, file_obj=filer_file.file, **kwargs)
        return response
