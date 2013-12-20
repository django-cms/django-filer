#-*- coding: utf-8 -*-
import inspect
from filer import settings
from django.contrib import admin
from filer.fields import folder


class PermissionAdmin(admin.ModelAdmin):
    list_display = ('who_combined', 'subject_combined', 'can_read', 'can_edit',)
    list_filter = ('who', 'subject', 'can_read', 'can_edit')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email',
                     'group__name', 'folder__name', 'file__name')
    fieldsets = (
        (None, {'fields': ('who', ('user', 'group',))}),
        (None, {'fields': ('subject', ('folder', 'file',),)}),
        (None, {'fields':
                (
                    ('can_read', 'can_edit', ),
                )}
        ),
    )
    raw_id_fields = ('user', 'group', 'file')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        db = kwargs.get('using')
        if db_field.name == 'folder':
            if 'admin_site' in inspect.getargspec(folder.AdminFolderWidget.__init__)[0]:
                # Django 1.4
                widget_instance = folder.AdminFolderWidget(db_field.rel, self.admin_site, using=db)
            else:
                # Django <= 1.3
                widget_instance = folder.AdminFolderWidget(db_field.rel, using=db)
            kwargs['widget'] = widget_instance
        return super(PermissionAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def who_combined(self, obj):
        if obj.who == 'user':
            return u'<strong>%s</strong> (User)' % obj.user
        elif obj.who == 'group':
            return u'<strong>%s</strong> (Group)' % obj.group
        return u'<strong>%s</strong>' % obj.get_who_display()
    who_combined.allow_tags = True
    who_combined.short_description = 'who'
    who_combined.admin_order_field = 'who'

    def subject_combined(self, obj):
        if obj.subject == 'file':
            return u'<img src="%s" /> <strong>%s</strong> (File)' % (obj.file.icons['16'], obj.file,)
        elif obj.subject == 'folder':
            return u'<img src="%s" /> <strong>%s</strong> (Folder)' % (obj.folder.icons['16'], obj.folder,)
        return u'<strong>%s</strong>' % obj.get_subject_display()
    subject_combined.allow_tags = True
    subject_combined.short_description = 'subject'
    subject_combined.admin_order_field = 'subject'

    def get_model_perms(self, request):
        # don't display the permissions admin if permissions are disabled.
        # This method is easier for testing than not registering the admin at all at import time
        enable_permissions = settings.FILER_ENABLE_PERMISSIONS\
            and request.user.has_perm('filer.add_permission')
        return {
            'add': enable_permissions,
            'change': enable_permissions,
            'delete': enable_permissions,
        }
