.. _server:

Server
======

django-filer supports permissions on files. They can be enabled or disabled.
Files with disabled permissions are your regular world readable files in
``MEDIA_ROOT``. Files with permissions are a other case however. To be able to
check permissions on the file downloads a special view is used and they are
saved in a separate location. The default is a directory called ``smedia`` next
to ``MEDIA_ROOT`` that must *NOT* be served by the webserver directly.

``filer.server.urls`` needs to be included in the root ``urls.py``::

    urlpatterns += patterns('',
        url(r'^', include('filer.server.urls')),
    )

The view will serve the permission-checked media files by delegating to one of
its server backends. The ones bundled with django-filer live in
``filer.server.backends`` and it is easy to create new ones.

The default is ``filer.server.backends.default.DefaultServer``. It is suitable
for development and serves the file directly from django.

More suitiable for production are server backends that delegate the actual file
serving to an upstream webserver.

``NginxXAccelRedirectServer``
-----------------------------

location: ``filer.server.backends.nginx.NginxXAccelRedirectServer``

nginx docs about this stuff: http://wiki.nginx.org/XSendfile

in ``settings.py``::

    from filer.server.backends.nginx import NginxXAccelRedirectServer
    
    FILER_PRIVATEMEDIA_ROOT = '/path/to/smedia/filer'
    FILER_PRIVATEMEDIA_URL = '/smedia/filer/'
    FILER_PRIVATEMEDIA_SERVER = NginxXAccelRedirectServer(
                                   location=FILER_PRIVATEMEDIA_ROOT,
                                   nginx_location='/nginx_filer_private')
    
    FILER_PRIVATEMEDIA_THUMBNAIL_ROOT = '/path/to/smedia/filer_thumbnails'
    FILER_PRIVATEMEDIA_THUMBNAIL_URL = '/smedia/filer_thumbnails/'
    FILER_PRIVATEMEDIA_THUMBNAIL_SERVER = NginxXAccelRedirectServer(
                                   location=FILER_PRIVATEMEDIA_THUMBNAIL_ROOT,
                                   nginx_location='/nginx_filer_private_thumbnails')

``nginx_location`` is the location directive where nginx "hides"
permission-checked files from general access. A fitting nginx configuration
might look something like this::
    
    location /nginx_filer_private/ {
      internal;
      alias /path/to/smedia/filer/;
    }
    location /nginx_filer_private_thumbnails/ {
      internal;
      alias /path/to/smedia/filer_thumbnails/;
    }

.. Note::
   make sure you follow the example exactly. Missing trailing slashes and ``alias`` vs.
   ``root`` have subtle differences that can make your config fail.

``NginxXAccelRedirectServer`` will add the a ``X-Accel-Redirect`` header to 
the response instead of actually loading and delivering the file itself. The 
value in the header will be something like 
``/nginx_filer_private/2011/03/04/myfile.pdf``. Nginx picks this up and does
the actual file delivery while the django backend is free to do other stuff
again.

``ApacheXSendfileServer``
-------------------------

location: ``filer.server.backends.xsendfile.ApacheXSendfileServer``

.. Warning::
   I have not tested this myself. Any feedback and example configurations are
   very welcome :-)

Once you have ``mod_xsendfile`` installed on your apache server you can
configure the settings.

in ``settings.py``::
    
    from filer.server.backends.xsendfile import ApacheXSendfileServer
    
    FILER_PRIVATEMEDIA_SERVER = ApacheXSendfileServer()
    FILER_PRIVATEMEDIA_THUMBNAIL_SERVER = ApacheXSendfileServer()

in your apache configuration::
    
    XSendFilePath /path/to/smedia/

``XSendFilePath`` is a whitelist for directories where apache will serve files
from.
