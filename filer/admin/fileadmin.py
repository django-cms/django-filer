# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django import forms
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from .. import settings
from ..models import File
from ..utils.compatibility import unquote
from ..vendor.publisher.admin import PublisherAdminMixin
from .permissions import PrimitivePermissionAwareModelAdmin
from .tools import AdminContext, admin_url_params_encoded, popup_status


class FileAdminChangeFrom(forms.ModelForm):
    class Meta(object):
        model = File
        exclude = ()


class FileAdmin(PublisherAdminMixin, PrimitivePermissionAwareModelAdmin):
    change_form_template = 'admin/filer/file/change_form.html'
    list_display = ('label',)
    list_per_page = 10
    search_fields = ['name', 'original_filename', 'sha1', 'description']
    raw_id_fields = ('owner',)
    readonly_fields = (
        'file_info',
        'file_info_with_picker',
        'sha1',
        'display_canonical',
    )
    extra_main_fields = ()
    extra_advanced_fields = ()
    extra_fieldsets = ()

    form = FileAdminChangeFrom

    def get_fieldsets(self, request, obj=None):
        admin_context = AdminContext(request)
        if admin_context['popup'] and admin_context['pick_file']:
            file_info_field = 'file_info_with_picker'
        else:
            file_info_field = 'file_info'
        fieldsets = (
            (None, {
                'classes': ('filer-file-info',),
                'fields': (
                    file_info_field,
                ),
            }),
            (' ', {
                'fields': (
                    'name',
                    'owner',
                    'description',
                ) + tuple(self.extra_main_fields),
            }),
            (_('Advanced'), {
                'fields': (
                    'file',
                    'sha1',
                    'display_canonical',
                ) + tuple(self.extra_advanced_fields),
                'classes': ('collapse',),
            }),
        ) + tuple(self.extra_fieldsets)
        if settings.FILER_ENABLE_PERMISSIONS:
            fieldsets = fieldsets + (
                (None, {
                    'fields': ('is_public',)
                }),
            )
        return fieldsets

    def get_is_readonly_view(self, obj):
        if settings.FILER_ENABLE_PUBLISHER:
            return obj.publisher_is_published_version
        else:
            return (
                obj.publisher_is_published_version and
                obj.publisher_has_pending_changes
            )

    def get_readonly_fields(self, request, obj=None):
        if not self.get_is_readonly_view(obj):
            # We don't want the get_readonly_fields in DraftLiveAdminMixin
            # to make the form readonly. So we call super on the other base
            # class to get the default implementation.
            return (
                super(PrimitivePermissionAwareModelAdmin, self)
                .get_readonly_fields(request, obj=obj)
            )
        return super(FileAdmin, self).get_readonly_fields(request, obj=obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {} if extra_context is None else extra_context
        # Double query. Sad.
        obj = self.get_object(request, unquote(object_id))
        extra_context['draft_workflow_buttons'] = self.publisher_get_buttons(request, obj)
        return self.changeform_view(request, object_id, form_url, extra_context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        add = object_id is None
        if (
            not add and
            settings.FILER_ENABLE_PUBLISHER and
            request.method == 'POST'
        ):
            # Check permissions for publisher actions
            obj = self.get_object(request, unquote(object_id))
            allowed_actions = [
                '_{}'.format(action)
                for action in obj.publisher_allowed_actions(request.user)
            ]
            if (
                obj and obj.publisher_is_published_version and
                not any([
                    allowed_action in request.POST
                    for allowed_action in allowed_actions
                ])
            ):
                raise PermissionDenied
        return (
            super(FileAdmin, self)
            .changeform_view(
                request,
                object_id=object_id,
                form_url=form_url,
                extra_context=extra_context,
            )
        )

    def publisher_get_admin_changelist_url(self, obj=None):
        return self.get_admin_directory_listing_url_for_obj(obj)

    def get_admin_directory_listing_url_for_obj(self, obj):
        if obj and obj.pk and obj.folder_id:
            return reverse(
                'admin:filer-directory_listing',
                kwargs={'folder_id': obj.folder_id},
            )
        else:
            return reverse('admin:filer-directory_listing-unfiled_images')

    def response_change(self, request, obj):
        """
        Overrides the default to be able to forward to the directory listing
        instead of the default change_list_view and handles the draft/live
        related actions.
        We also handle our special draft/live workflow cases here, because they
        rely on changes to the object that need to be saved already.
        """
        if request.POST and '_create_draft' in request.POST:
            draft = obj.publisher_create_draft()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(draft))
        elif request.POST and '_discard_draft' in request.POST:
            live = obj.publisher_get_live_version()
            obj.discard_draft()
            return HttpResponseRedirect(self.publisher_get_detail_or_changelist_url(live))
        elif request.POST and '_publish' in request.POST:
            live = obj.publisher_publish()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(live))
        elif request.POST and '_request_deletion' in request.POST:
            live = obj.publisher_request_deletion()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(live))
        elif request.POST and '_discard_requested_deletion' in request.POST:
            obj.publisher_discard_requested_deletion()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(obj))
        elif request.POST and '_publish_deletion' in request.POST:
            obj.publisher_publish_deletion()
            return HttpResponseRedirect(self.publisher_get_admin_changelist_url(obj))
        elif (
            request.POST and
            '_continue' not in request.POST and
            '_saveasnew' not in request.POST and
            '_addanother' not in request.POST
        ):
            # Popup in pick mode or normal mode. In both cases we want to go
            # back to the folder list view after save. And not the useless file
            # list view.
            url = self.get_admin_directory_listing_url_for_obj(obj)
            url = "{0}{1}".format(
                url,
                admin_url_params_encoded(request),
            )
            return HttpResponseRedirect(url)

        return super(FileAdmin, self).response_change(request, obj)

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        info = self.model._meta.app_label, self.model._meta.model_name
        extra_context = {
            'history_url': 'admin:%s_%s_history' % info,
            'is_popup': popup_status(request),
            'filer_admin_context': AdminContext(request),
        }
        context.update(extra_context)
        return super(FileAdmin, self).render_change_form(
            request=request, context=context, add=add, change=change,
            form_url=form_url, obj=obj)

    def delete_view(self, request, object_id, extra_context=None):
        """
        Overrides the default to enable redirecting to the directory view after
        deletion of a image.

        we need to fetch the object and find out who the parent is
        before super, because super will delete the object and make it
        impossible to find out the parent folder to redirect to.
        """
        try:
            obj = self.get_queryset(request).get(pk=unquote(object_id))
            parent_folder = obj.folder
        except self.model.DoesNotExist:
            parent_folder = None

        if request.POST:
            # Return to folder listing, since there is no usable file listing.
            super(FileAdmin, self).delete_view(
                request=request, object_id=object_id,
                extra_context=extra_context)
            if parent_folder:
                url = reverse('admin:filer-directory_listing',
                              kwargs={'folder_id': parent_folder.id})
            else:
                url = reverse('admin:filer-directory_listing-unfiled_images')
            url = "{0}{1}".format(
                url,
                admin_url_params_encoded(request)
            )
            return HttpResponseRedirect(url)

        return super(FileAdmin, self).delete_view(
            request=request, object_id=object_id,
            extra_context=extra_context)

    def get_model_perms(self, request):
        """
        These permissions are only used in the admin index view, causing
        Files to not appear in the global list. We allow navigating to it
        through the directory listing instead.
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }

    def has_publish_permission(self, request, obj=None):
        return obj.user_can_publish(request.user)

    def has_delete_permission(self, request, obj=None):
        if not settings.FILER_ENABLE_PUBLISHER:
            # Skip the draft/live logic of live objects when the feature is
            # disabled.
            return PrimitivePermissionAwareModelAdmin.has_delete_permission(self, request, obj)
        return super(FileAdmin, self).has_delete_permission(request, obj)

    def display_canonical(self, instance):
        canonical = instance.canonical_url
        if canonical:
            return '<a href="%s">%s</a>' % (canonical, canonical)
        else:
            return '-'
    display_canonical.allow_tags = True
    display_canonical.short_description = _('canonical URL')

    def get_file_info_context(self, obj):
        return {
            'original': obj,
            'fileype': 'file',
            'is_readonly': self.get_is_readonly_view(obj),
        }

    def file_info(self, obj):
        context = self.get_file_info_context(obj)
        return render_to_string('admin/filer/tools/file_info.html', context)
    file_info.allow_tags = True
    file_info.short_description = ''

    def file_info_with_picker(self, obj):
        context = self.get_file_info_context(obj)
        context['filer_show_picker'] = True
        return render_to_string('admin/filer/tools/file_info.html', context)
    file_info_with_picker.allow_tags = True
    file_info_with_picker.short_description = ''
