from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .. import settings


class PermissionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['type', 'folder']}),
        (_("Who"), {'fields': ['user', 'group', 'everybody']}),
        (_("What"), {'fields': ['can_edit', 'can_read', 'can_add_children']}),
    ]
    list_filter = ['group']
    list_display = ['pretty_logical_path', 'who', 'what']
    search_fields = ['user__username', 'group__name', 'folder__name']
    autocomplete_fields = ['user', 'group', 'folder']

    class Media:
        css = {'all': ['filer/css/admin_folderpermissions.css']}

    def get_queryset(self, request):
        qs = super(PermissionAdmin, self).get_queryset(request)
        return qs.prefetch_related("group", "folder")

    def get_model_perms(self, request):
        # don't display the permissions admin if permissions are disabled.
        # This method is easier for testing than not registering the admin at all at import time
        enable_permissions = settings.FILER_ENABLE_PERMISSIONS and request.user.has_perm('filer.add_folderpermission')
        return {
            'add': enable_permissions,
            'change': enable_permissions,
            'delete': enable_permissions,
        }
