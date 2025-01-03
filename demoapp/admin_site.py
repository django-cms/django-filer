from django.contrib import admin

from finder.admin.folder import FolderAdmin
from finder.models.folder import FolderModel


class DempappAdminSite(admin.AdminSite):
    pass


admin_site = DempappAdminSite(name="demoapp_admin")
admin_site.register(FolderModel, FolderAdmin)
