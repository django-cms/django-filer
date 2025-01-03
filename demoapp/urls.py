"""demoapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from finder.browser import urls as browser_urls

from demoapp.views import DemoAppView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('finder-api/', include(browser_urls)),  # endpoints for demoapp
    path('demoapp/', DemoAppView.as_view(), name='demoapp'),
]
if settings.DEBUG:
    urlpatterns.extend(static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    ))
