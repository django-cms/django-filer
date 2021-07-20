from django.contrib import admin

from .. import settings
from ..fields import folder


class PermissionAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': (('type', 'folder', ))}),
        (None, {'fields': (('user', 'group', 'everybody'), )}),
        (None, {'fields': (
            ('can_edit', 'can_read', 'can_add_children')
        )}),
    )
    raw_id_fields = ['user', 'group']
    list_filter = ['group']
    list_display = ['__str__', 'folder', 'user']
    search_fields = ['user__username', 'group__name', 'folder__name']

    def get_queryset(self, request):
        qs = super(PermissionAdmin, self).get_queryset(request)
        return qs.prefetch_related("group", "folder")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        db = kwargs.get('using')
        if db_field.name == 'folder':
            kwargs['widget'] = folder.AdminFolderWidget(db_field.remote_field, self.admin_site, using=db)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_model_perms(self, request):
        # don't display the permissions admin if permissions are disabled.
        # This method is easier for testing than not registering the admin at all at import time
        enable_permissions = settings.FILER_ENABLE_PERMISSIONS and request.user.has_perm('filer.add_folderpermission')
        return {
            'add': enable_permissions,
            'change': enable_permissions,
            'delete': enable_permissions,
        }
