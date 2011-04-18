Server
======

django-filer can handle public and private files. Public files are your regular
world readable files in ``MEDIA_ROOT``. Private files are a other case however.
To be able to check permissions on the file downloads a special view is used and
they are saved in a separate location. The default is a directory called 
``smedia`` next to ``MEDIA_ROOT`` that must *NOT* be served by the webserver
directly.

``filer.server.urls`` needs to be included in the root ``urls.py``::

    urlpatterns += patterns('',
        url(r'^', include('filer.server.urls')),
    )

The view will serve the private media files by delegating to one of its server
backends. The ones bundled with django-filer live in ``filer.server.backends``
and it is easy to create new ones.

The default is ``filer.server.backends.default.DefaultServer``. It is suitable
for development and serves the file directly from django.

More suitiable for production are server backends that delegate the actual file
serving to an upstream webserver.

``filer.server.backends.nginx.NginxXAccelRedirectServer``
---------------------------------------------------------

in settings.py::

    from filer.server.backends.nginx import NginxXAccelRedirectServer
    
    FILER_PRIVATEMEDIA_ROOT = '/path/to/smedia/filer'
    FILER_PRIVATEMEDIA_URL = '/smedia/filer/'
    FILER_PRIVATEMEDIA_SERVER = NginxXAccelRedirectServer(
                                   location=FILER_PRIVATEMEDIA_ROOT,
                                   nginx_location='nginx_filer_private')
    
    FILER_PRIVATEMEDIA_THUMBNAIL_ROOT = '/path/to/smedia/filer_thumbnails'
    FILER_PRIVATEMEDIA_THUMBNAIL_URL = '/smedia/filer_thumbnails'
    FILER_PRIVATEMEDIA_THUMBNAIL_SERVER = NginxXAccelRedirectServer(
                                   location=FILER_PRIVATEMEDIA_ROOT,
                                   nginx_location='nginx_filer_private_thumbnails')

``nginx_location`` is the location directive where nginx "hides" private files
from general access. A fitting nginx configuration might look something like
this::
    
    location /nginx_filer_private/ {
      internal;
      root   /path/to/smedia/filer;
    }
    location /nginx_filer_private_thumbnails/ {
      internal;
      root   /path/to/smedia/filer_thumbnails;
    }

``NginxXAccelRedirectServer`` will add the a ``X-Accel-Redirect`` header to 
the response instead of actually loading and delivering the file itself. The 
value in the header will be something like 
``/nginx_filer_private/2011/03/04/myfile.pdf``. Nginx picks this up and does
the actual file delivery while the django backend is free to do other stuff
again.

``filer.server.backends.xsendfile.ApacheXSendfileServer``
---------------------------------------------------------

.. TODO: add docs
