from django.conf import settings
from django.contrib import admin
from django.urls import include, re_path
from django.views.static import serve


admin.autodiscover()
admin_urls = admin.site.urls

urlpatterns = [
    re_path(r'^media/(?P<path>.*)$', serve,
            {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    re_path(r'^admin/', admin_urls),
    re_path(r'^', include('filer.server.urls')),
    re_path(r'^filer/', include('filer.urls')),
]
