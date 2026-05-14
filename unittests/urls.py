from django.contrib import admin
from django.urls import include, path

from finder.browser import urls as browser_urls

from .testapp.views import TestAppView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('finder-api/', include(browser_urls)),  # endpoints for demoapp
    path('testapp/', TestAppView.as_view(), name='testapp'),
]
