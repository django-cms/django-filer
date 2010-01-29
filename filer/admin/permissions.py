from django.contrib import admin

class PrimitivePermissionAwareModelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # we don't have a "add" permission... but all adding is handled
        # by special methods that go around these permissions anyway
        # TODO: reactivate return False
        return False
    def has_change_permission(self, request, obj=None):
        if hasattr(obj, 'has_edit_permission'):
            if obj.has_edit_permission(request):
                #print "%s has edit permission for %s" % (request.user, obj)
                return True
            else:
                #print "%s has NO edit permission for %s" % (request.user, obj)
                return False
        else:
            return True
        
    def has_delete_permission(self, request, obj=None):
        # we don't have a specific delete permission... so we use change
        return self.has_change_permission(request, obj)