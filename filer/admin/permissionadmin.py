from django.contrib import admin

from .. import settings


class PermissionAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['type', 'folder']}),
        (None, {'fields': ['user', 'group', 'everybody']}),
        (None, {'fields': ['can_edit', 'can_read', 'can_add_children']}),
    ]
    autocomplete_fields = ['user', 'group']
    list_filter = ['user']
    list_display = ['__str__', 'folder', 'user']

    def get_model_perms(self, request):
        # don't display the permissions admin if permissions are disabled.
        # This method is easier for testing than not registering the admin at all at import time
        enable_permissions = settings.FILER_ENABLE_PERMISSIONS and request.user.has_perm('filer.add_folderpermission')
        return {
            'add': enable_permissions,
            'change': enable_permissions,
            'delete': enable_permissions,
        }
