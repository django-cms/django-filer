from django.contrib import admin

from finder.admin.folder import FolderAdmin
from finder.models.folder import FolderModel


class DemoappAdminSite(admin.AdminSite):
    """
    Test if django-filer also works in with multiple tennants.
    """


admin_site = DemoappAdminSite(name="demoapp_admin")
admin_site.register(FolderModel, FolderAdmin)
