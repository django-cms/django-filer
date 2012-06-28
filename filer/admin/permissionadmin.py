#-*- coding: utf-8 -*-
from django.contrib import admin
from filer.fields import folder


class PermissionAdmin(admin.ModelAdmin):
    list_display = ('edit', 'who_combined', 'subject_combined', 'can', 'is_inheritable',)
    list_filter = ('who', 'subject', 'can', 'is_inheritable',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email',
                     'group__name',)
    fieldsets = (
        (None, {'fields': ('who', ('user', 'group',))}),
        (None, {'fields': ('subject', ('folder', 'file',),)}),
        (None, {'fields': (
                    ('can', 'is_inheritable', ),
                    )}
        ),
    )
    raw_id_fields = ('user', 'group', 'file')

    def edit(self, obj):
        return 'edit'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        db = kwargs.get('using')
        if db_field.name == 'folder':
            kwargs['widget'] = folder.AdminFolderWidget(db_field.rel, using=db)
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