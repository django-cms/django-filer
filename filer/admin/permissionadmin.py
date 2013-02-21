#-*- coding: utf-8 -*-
import inspect
from django.contrib import admin
from filer import settings
from filer.fields import folder


class PermissionAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': (('type', 'folder',))}),
        (None, {'fields': (('user', 'group', 'everybody'),)}),
        (None, {'fields': (
                    ('can_edit', 'can_read', 'can_add_children')
                    )}
        ),
    )
    raw_id_fields = ('user', 'group',)
    list_filter = ['user']
    list_display = ['__unicode__', 'folder', 'user']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        db = kwargs.get('using')
        if db_field.name == 'folder':
            if 'admin_site' in inspect.getargspec(folder.AdminFolderWidget.__init__)[0]: # Django 1.4
                widget_instance = folder.AdminFolderWidget(db_field.rel, self.admin_site, using=db)
            else: # Django <= 1.3
                widget_instance = folder.AdminFolderWidget(db_field.rel, using=db)
            kwargs['widget'] = widget_instance
        return super(PermissionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_model_perms(self, request):
        # don't display the permissions admin if permissions are disabled.
        # This method is easier for testing than not registering the admin at all at import time
        enable_permissions = settings.FILER_ENABLE_PERMISSIONS and request.user.has_perm('filer.add_folderpermission')
        return {
            'add': enable_permissions,
            'change': enable_permissions,
            'delete': enable_permissions,
        }
