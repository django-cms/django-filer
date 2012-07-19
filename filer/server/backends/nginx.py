#-*- coding: utf-8 -*-
from django.http import HttpResponse
from filer.server.backends.base import ServerBase


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

    def serve(self, request, file_obj, **kwargs):
        # we should not use get_mimetype() here, because it tries to access the file in the filesystem.
        #response = HttpResponse(mimetype=self.get_mimetype(file.path))
        response = HttpResponse()
        nginx_path = self.get_nginx_location(file_obj.path)
        response['X-Accel-Redirect'] = nginx_path
        self.default_headers(request=request, response=response, file_obj=file_obj, **kwargs)
        return response
