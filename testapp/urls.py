"""testapp URL Configuration

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
from django.http import HttpResponse
from django.template.loader import get_template
from django.urls import path

from testapp.admin_site import admin_site


def render_landing(request):
    template = get_template('testapp.html')
    context = {}
    return HttpResponse(template.render(context))


urlpatterns = [
    path('admin/', admin.site.urls),
    path('testapp/admin/', admin_site.urls),
    path('testapp/', render_landing),
]
if settings.DEBUG:
    urlpatterns.extend(static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    ))
