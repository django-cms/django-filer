# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib import admin
from django.core.urlresolvers import reverse


class PrimitivePermissionAwareModelAdmin(admin.ModelAdmin):
    # FIXME: this class should be refactored to use only built-in Django permission handling
    # but with obj being passed. Then we can implement auth backend for filer which would do permission
    # checking for filer models only. It would just use existing obj.has_edit_permission, etc.
    # So if someone wants to override permission checking they could use whatever they want from existing
    # Django permission handling apps supporting obj-level permissions (like django-rules or
    # django-guardian). When permission handling is overriden, FILER_ENABLE_PERMISSIONS setting would be
    # False. When it is True (using integrated filer permissions), we could have some system check to see
    # if filer auth backend is in AUTH_BACKENDS setting.
    # However, there are a few tricky parts to this:
    # * filer's read permission could be changed to 'view' permission which is available since Django 2.1.
    #   It would still have to be enabled through File and Folder Meta.default_permissions.
    # * 'add' permission in filer uses related folder (so obj should be a folder while permission being
    #   checked is either 'add_file' or 'add_folder'. This kind of behavior (obj for add where obj model
    #   does not necessarily match permission model) is already used for inline admin permission checking
    #   in Django 2.1 therefore it's not something non-standard.
    # * When checking 'change' or 'delete' permissions for files, permissions should always match File content
    #   type instead of specific File subclasses so 'change_image' would never be used for example. This is
    #   also a common practice when checking permissions for polymorphic models.
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
        # FIXME: remove. This is not used.
        # Code from django ModelAdmin to determine changelist on the fly
        opts = obj._meta
        return reverse('admin:%s_%s_changelist' %
                       (opts.app_label, opts.model_name),
            current_app=self.admin_site.name)
