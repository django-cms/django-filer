from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve


admin.autodiscover()
admin_urls = admin.site.urls

urlpatterns = [
    path('media/my-preferred-base-url-for-source-files/<path:path>', serve,
         {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    path('media/my-preferred-base-url-for-thumbnails/<path:path>', serve,
         {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}),
    path('admin/', admin_urls),
    path('', include('filer.server.urls')),
    path('filer/', include('filer.urls')),
]
