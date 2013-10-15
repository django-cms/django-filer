#-*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext  as _
from filer.admin.common_admin import FilePermissionModelAdmin


class FileAdmin(FilePermissionModelAdmin):
    list_display = ('label',)
    list_per_page = 10
    search_fields = ['name', 'original_filename', 'sha1', 'description']
    raw_id_fields = ('owner',)
    readonly_fields = ('sha1', )


    # save_as hack, because without save_as it is impossible to hide the
    # save_and_add_another if save_as is False. To show only save_and_continue
    # and save in the submit row we need save_as=True and in
    # render_change_form() override add and change to False.
    save_as = True

    def get_readonly_fields(self, request, obj=None):
        if obj and (obj.is_readonly() or
                    obj.is_restricted_for_user(request.user)):
            return [field.name
                    for field in obj.__class__._meta.fields]
        self.readonly_fields = [ro_field
                                for ro_field in self.readonly_fields]
        self._make_restricted_field_readonly(request.user, obj)
        if not request.user.is_superuser:
            # allow owner to be editable only by superusers
            self.readonly_fields += ['owner']
        return super(FileAdmin, self).get_readonly_fields(
            request, obj)

    @classmethod
    def build_fieldsets(cls, extra_main_fields=(), extra_advanced_fields=(), extra_fieldsets=()):
        fieldsets = (
            (None, {
                'fields': ('name', 'owner', 'description',) + extra_main_fields,
            }),
            (_('Advanced'), {
                # due to custom requirements: sha1 field should be hidden
                # 'fields': ('file', 'sha1',) + extra_advanced_fields,
                'fields': ('file', ) + extra_advanced_fields,
                'classes': ('collapse',),
                }),
            (('Permissions'), {
                'fields': ('restricted',),
                'classes': ('collapse', 'wide', 'extrapretty'),
                })
            ) + extra_fieldsets
        return fieldsets

    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }

FileAdmin.fieldsets = FileAdmin.build_fieldsets()
