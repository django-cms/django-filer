Configuration
=============

1. In settings.py select the server to serve the files.

The static server must be selected to serve two types of urls under
FILER_PRIVATEMEDIA_URL:

   * protected urls:

     FILER_PRIVATEMEDIA_URL/file/<id>/*
     FILER_PRIVATEMEDIA_URL/thumb/<id>/*

   * unprotected urls, everything else under FILER_PRIVATEMEDIA_URL, as
     provided by the underlying Storage:

     FILER_PRIVATEMEDIA_URL/*

The following servers can be configured:

   * FILER_PRIVATEMEDIA_SERVER = 'filer.server.UnprotectedServer'

     This is the default. Will allow access to unprotected urls. Filer will
     generate protected urls for private files. UnprotectedServer will redirect
     protected urls to matching unprotected urls. A user without read permissions
     can access unprotected urls. Protected urls will be blocked before they are
     redirected.

   * FILER_PRIVATEMEDIA_SERVER = 'filer.server.DjangoStaticServer'

     Will serve protected files using django.views.static.serve.
     It will block access to unprotected urls.

   * FILER_PRIVATEMEDIA_SERVER = 'filer.server.ApacheXSendfileServer'

     Works like DjangoStaticServer but uses X-Sendfile to send files.

   * FILER_PRIVATEMEDIA_SERVER = None

     No server will be used and filer won't generate protected urls for
     protected files.

2. In urls.py add urls for protected files.

The filer urls must be added before the urls for other static files under
MEDIA_URL::

   urlpatterns += patterns('',
       url(r'^', include('filer.urls')),
   )
   ...
   urlpatterns += patterns('',
      url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
          {'document_root': settings.MEDIA_ROOT, 'show_indexes': True})
   )

If the filer.urls are not added to urlpatterns, all files will be freely
accessible with unprotected urls.
