from django.http import HttpResponse

from .base import ServerBase


class NginxXAccelRedirectServer(ServerBase):
    """
    This returns a response with only headers set, so that nginx actually does
    the serving
    """
    def __init__(self, location, nginx_location):
        """
        nginx_location
        """
        self.location = location
        self.nginx_location = nginx_location

    def get_nginx_location(self, path):
        return path.replace(self.location, self.nginx_location)

    def serve(self, request, filer_file, **kwargs):
        response = HttpResponse()
        response['Content-Type'] = filer_file.mime_type
        nginx_path = self.get_nginx_location(filer_file.path)
        response['X-Accel-Redirect'] = nginx_path
        self.default_headers(request=request, response=response, file_obj=filer_file.file, **kwargs)
        return response
