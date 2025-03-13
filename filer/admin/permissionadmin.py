from django import VERSION as django_version
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .. import settings
from ..cache import clear_folder_permission_cache


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

    def get_autocomplete_fields(self, request):
        """Remove "owner" from autocomplete_fields is User model has no search_fields"""

        autocomplete_fields = super().get_autocomplete_fields(request)
        if django_version >= (5, 0):
            user_admin = self.admin_site.get_model_admin(get_user_model())
        else:
            user_admin = self.admin_site._registry[get_user_model()]
        if not user_admin.get_search_fields(request):
            autocomplete_fields.remove('user')
        return autocomplete_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
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

    def save_model(self, request, obj, form, change):
        clear_folder_permission_cache(request.user)
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        clear_folder_permission_cache(request.user)
        super().delete_model(request, obj)
