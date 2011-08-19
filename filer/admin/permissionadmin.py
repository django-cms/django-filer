#-*- coding: utf-8 -*-
from django.contrib import admin
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        db = kwargs.get('using')
        if db_field.name == 'folder':
            kwargs['widget'] = folder.AdminFolderWidget(db_field.rel, using=db)
        return super(PermissionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
