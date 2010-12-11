from django.conf.urls.defaults import *
import settings

_private_root = settings.FILER_PRIVATEMEDIA_URL.lstrip("/")
print "Filer: " + _private_root
urlpatterns = patterns('filer.views',
    # This url is generated in filer.models.filemodels.protected_url()
    url(r'^' + _private_root + r'/file/(?P<file_id>[0-9]+)/.*$',
        'serve_protected_file',),

    url(r'^' + _private_root + r'/thumb/(?P<file_id>[0-9]+)/(?P<file_name>.*)$',
        'serve_protected_thumbnail',),

    url(r'^' + _private_root + r'/(?P<path>.*)$',
        'direct_file_access',),
)
