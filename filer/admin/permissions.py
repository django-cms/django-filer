from django import VERSION as django_version
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse


class PrimitivePermissionAwareModelAdmin(admin.ModelAdmin):
    def get_autocomplete_fields(self, request):
        """Remove "owner" from autocomplete_fields is User model has no search_fields"""

        autocomplete_fields = super().get_autocomplete_fields(request)
        if django_version >= (5, 0):
            user_admin = self.admin_site.get_model_admin(get_user_model())
        else:
            user_admin = self.admin_site._registry[get_user_model()]
        if not user_admin.get_search_fields(request) and 'owner' in autocomplete_fields:
            autocomplete_fields.remove('owner')
        return autocomplete_fields

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
        return reverse('admin:%s_%s_changelist' %
                       (opts.app_label, opts.model_name),
            current_app=self.admin_site.name)
