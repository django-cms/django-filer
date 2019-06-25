# -*- coding: utf-8 -*-
from __future__ import absolute_import

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

    def serve(self, request, file_obj, **kwargs):
        response = HttpResponse()
        response['Content-Type'] = file_obj.mime_type
        nginx_path = self.get_nginx_location(file_obj.path)
        response['X-Accel-Redirect'] = nginx_path
        self.default_headers(request=request, response=response, file_obj=file_obj, **kwargs)
        return response
