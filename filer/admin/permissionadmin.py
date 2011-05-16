#-*- coding: utf-8 -*-
from django.contrib import admin


class PermissionAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': (('type', 'folder',))}),
        (None, {'fields': (('user', 'group', 'everybody'),)}),
        (None, {'fields': (
                    ('can_edit', 'can_read', 'can_add_children')
                    )}
        ),
    )
    raw_id_fields = ('folder', 'user', 'group',)
