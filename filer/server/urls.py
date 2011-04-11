#-*- coding: utf-8 -*-
from django.conf.urls.defaults import patterns, url
from filer import settings as filer_settings

# Only add slashes if there is a value for the file or thumbnail prefixes
if filer_settings.FILER_PRIVATEMEDIA_FILE_URL_PREFIX:
    file_prefix = filer_settings.FILER_PRIVATEMEDIA_FILE_URL_PREFIX + "/"
else:
    file_prefix = ''
if filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_URL_PREFIX:
    thumb_prefix = filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_URL_PREFIX + "/"
else:
    thumb_prefix = ''

urlpatterns = patterns('filer.server.views',
    # This url is generated in filer.models.filemodels.url
    url(r'^' + file_prefix + r'(?P<path>.*)$', 'serve_protected_file',),

#    # This url is generated in filer.templatetags.filer_image_tags.WrapPrivateThumbnailFile
    url(r'^' + thumb_prefix + r'(?P<path>.*)$', 'serve_protected_thumbnail',),
)

#if static_server != None and not static_server.allowsDirectAccess:
#    urlpatterns += patterns('filer.views',
#        url(r'^' + _private_root + r'/(?P<path>.*)$',
#            'direct_file_access',),
#    )
