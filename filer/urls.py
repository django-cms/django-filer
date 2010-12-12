from django.conf.urls.defaults import *
from settings import FILER_PRIVATEMEDIA_URL
from settings import static_server

_private_root = FILER_PRIVATEMEDIA_URL.lstrip("/")
urlpatterns = patterns('filer.views',
    # This url is generated in filer.models.filemodels.url
    url(r'^' + _private_root + r'/file/(?P<file_id>[0-9]+)/.*$',
        'serve_protected_file',),

    # This url is generated in filer.templatetags.filer_image_tags.WrapPrivateThumbnailFile
    url(r'^' + _private_root + r'/thumb/(?P<file_id>[0-9]+)/(?P<file_name>.*)$',
        'serve_protected_thumbnail',),
)

if static_server != None and not static_server.allowsDirectAccess:
    urlpatterns += patterns('filer.views',
        url(r'^' + _private_root + r'/(?P<path>.*)$',
            'direct_file_access',),
    )
