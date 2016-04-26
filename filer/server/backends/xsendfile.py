# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.http import HttpResponse

from .base import ServerBase


class ApacheXSendfileServer(ServerBase):
    def serve(self, request, file_obj, **kwargs):
        response = HttpResponse()
        response['X-Sendfile'] = file_obj.path

        # This is needed for lighttpd, hopefully this will
        # not be needed after this is fixed:
        # http://redmine.lighttpd.net/issues/2076
        response['Content-Type'] = self.get_mimetype(file_obj.path)

        self.default_headers(request=request, response=response, file_obj=file_obj, **kwargs)
        return response
