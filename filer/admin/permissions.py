#-*- coding: utf-8 -*-
from django.contrib import admin
from django.core.urlresolvers import reverse


class PrimitivePermissionAwareModelAdmin(admin.ModelAdmin):

    def has_change_permission(self, request, obj=None):
        can_change = super(PrimitivePermissionAwareModelAdmin, self).\
            has_change_permission(request, obj)
        return getattr(obj, 'has_edit_permission', can_change)

    def has_delete_permission(self, request, obj=None):
        can_delete = super(PrimitivePermissionAwareModelAdmin, self).\
            has_change_permission(request, obj)
        # we don't have a specific delete permission... so we use change
        return getattr(obj, 'has_delete_permission', can_delete)

    def _get_post_url(self, obj):
        """
        Needed to retrieve the changelist url as Folder/File can be extended
            and admin url may change
        """
        # Code borrowed from django ModelAdmin to determine
        #      changelist on the fly
        opts = obj._meta
        module_name = opts.module_name
        return reverse('admin:%s_%s_changelist' %
                       (opts.app_label, module_name),
            current_app=self.admin_site.name)
