# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib import admin
from django.core.urlresolvers import reverse

from ..utils.compatibility import LTE_DJANGO_1_7


class PrimitivePermissionAwareModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # we don't have a "add" permission... but all adding is handled
        # by special methods that go around these permissions anyway
        # TODO: reactivate return False
        return False

    def has_change_permission(self, request, obj=None):
        if hasattr(obj, 'has_edit_permission'):
            if obj.has_edit_permission(request):
                return True
            else:
                return False
        else:
            return True

    def has_delete_permission(self, request, obj=None):
        # we don't have a specific delete permission... so we use change
        return self.has_change_permission(request, obj)

    def _get_post_url(self, obj):
        """
        Needed to retrieve the changelist url as Folder/File can be extended
        and admin url may change
        """
        # Code from django ModelAdmin to determine changelist on the fly
        opts = obj._meta
        if LTE_DJANGO_1_7:
            model_name = opts.module_name
        else:
            model_name = opts.model_name
        return reverse('admin:%s_%s_changelist' %
                       (opts.app_label, model_name),
            current_app=self.admin_site.name)
