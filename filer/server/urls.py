from django.conf.urls.defaults import *

urlpatterns = patterns('filer.server.views',
    # This url is generated in filer.models.filemodels.url
    url(r'^file/(?P<path>.*)$',
        'serve_protected_file',),

#    # This url is generated in filer.templatetags.filer_image_tags.WrapPrivateThumbnailFile
    url(r'^_/(?P<path>.*)$',
        'serve_protected_thumbnail',),
)

#if static_server != None and not static_server.allowsDirectAccess:
#    urlpatterns += patterns('filer.views',
#        url(r'^' + _private_root + r'/(?P<path>.*)$',
#            'direct_file_access',),
#    )
