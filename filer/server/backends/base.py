from django.utils.encoding import smart_str

class ServerBase(object):
    def __init__(self, *args, **kwargs):
        pass
    
    def default_headers(self, request, response, **kwargs):
        self.save_as_header(response, save_as=kwargs.get('save_as', False))
        self.size_header(response, file=kwargs.get('file',None), 
                                   size=kwargs.get('size',None))
    def save_as_header(self, response, save_as):
        if save_as:
            response['Content-Disposition'] = smart_str(u'attachment; filename=%s' % save_as)
    def size_header(self, response, file, size):
        if size:
            response['Content-Length'] = size
        elif file.size is not None:
            response['Content-Length'] = file.size