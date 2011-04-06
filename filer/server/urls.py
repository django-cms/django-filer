#-*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from filer import settings as filer_settings

urlpatterns = patterns('filer.server.views',
    # This url is generated in filer.models.filemodels.url
    url(r'^' + filer_settings.FILER_PRIVATEMEDIA_FILE_URL_PREFIX + r'/(?P<path>.*)$',
        'serve_protected_file',),

#    # This url is generated in filer.templatetags.filer_image_tags.WrapPrivateThumbnailFile
    url(r'^' + filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_URL_PREFIX + r'/(?P<path>.*)$',
        'serve_protected_thumbnail',),
)

#if static_server != None and not static_server.allowsDirectAccess:
#    urlpatterns += patterns('filer.views',
#        url(r'^' + _private_root + r'/(?P<path>.*)$',
#            'direct_file_access',),
#    )
