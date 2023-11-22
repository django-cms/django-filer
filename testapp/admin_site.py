from django.contrib import admin

from finder.admin.folder import FolderAdmin
from finder.models.folder import FolderModel


class TestappAdminSite(admin.AdminSite):
    pass


admin_site = TestappAdminSite(name="testapp_admin")
admin_site.register(FolderModel, FolderAdmin)
