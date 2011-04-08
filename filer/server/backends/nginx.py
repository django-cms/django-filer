#-*- coding: utf-8 -*-
from django.http import HttpResponse
from filer.server.backends.base import ServerBase
from filer import settings as filer_settings

class NginxXAccelRedirectServer(ServerBase):
    '''
    This returns a response with only headers set, so that nginx actually does
    the serving
    '''
    def __init__(self, *args, **kwargs):
        self.nginx_protected_location = kwargs.get('nginx_location', filer_settings.FILER_NGINX_PROTECTED_LOCATION)
        self.nginx_protected_root = filer_settings.FILER_PRIVATEMEDIA_ROOT
    def get_nginx_location(self, path):
        return '/' + path.replace(self.nginx_protected_root, self.nginx_protected_location)
    def serve(self, request, file, **kwargs):
        response = HttpResponse(mimetype=self.get_mimetype(file.path))
        nginx_path = self.get_nginx_location(file.path)
        response['X-Accel-Redirect'] = nginx_path
        self.default_headers(request=request, response=response, file=file, **kwargs)
        return response