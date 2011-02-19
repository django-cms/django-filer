from django.http import HttpResponse
from filer.server.backends.base import ServerBase
from filer import settings

class NginxXAccelRedirectServer(ServerBase):
    def __init__(self, *args, **kwargs):
        self.nginx_protected_location = kwargs.get('nginx_location', 'media_private')
        self.nginx_protected_root = settings.FILER_PRIVATEMEDIA_ROOT
    def get_nginx_location(self, path):
        return '/' + path.replace(self.nginx_protected_root, self.nginx_protected_location)
    def serve(self, request, file, **kwargs):
        response = HttpResponse(mimetype=self.get_mimetype(file.path))
        nginx_path = self.get_nginx_location(file.path)
        print nginx_path
        response['X-Accel-Redirect'] = nginx_path
        self.default_headers(request=request, response=response, file=file, **kwargs)
        return response