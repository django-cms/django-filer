#-*- coding: utf-8 -*-
from django.contrib import admin
from django.core.urlresolvers import reverse


class PrimitivePermissionAwareModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # We check permissions here instead of the default django implementation.
        # Otherwise we'd have to create a custom auth backend to make it work.
        # We don't have a "add" permission... but all adding is handled
        # by special methods that go around these permissions anyway
        return False

    def has_change_permission(self, request, obj=None):
        # We check permissions here instead of the default django implementation.
        # Otherwise we'd have to create a custom auth backend to make it work.
        if hasattr(obj, 'can_edit'):
            if obj.can_edit(request.user):
                return True
            else:
                return False
        else:
            return True

    def has_delete_permission(self, request, obj=None):
        # we don't have a specific delete permission... so we use change
        return self.has_change_permission(request, obj)

    def _get_post_url(self, obj):
        """ Needed to retrieve the changelist url as Folder/File can be extended
        and admin url may change """
        ## Code borrowed from django ModelAdmin to determine changelist on the fly
        opts = obj._meta
        module_name = opts.module_name
        return reverse('admin:%s_%s_changelist' %
                       (opts.app_label, module_name),
            current_app=self.admin_site.name)
