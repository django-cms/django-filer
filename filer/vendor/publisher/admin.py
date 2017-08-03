# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
from copy import copy

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from .utils.compat import PARLER_IS_INSTALLED


class PublisherAdminMixinBase(object):

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = (
            super(PublisherAdminMixinBase, self)
            .get_readonly_fields(request, obj=obj)
        )
        if not obj:
            return readonly_fields
        if obj.publisher_is_published_version:
            readonly_fields = set(readonly_fields)
            all_field_names = set(obj._meta.get_all_field_names())
            readonly_fields = readonly_fields | all_field_names
        return list(readonly_fields)

    def publisher_get_detail_or_changelist_url(self, obj):
        if not obj or obj and not obj.pk:  # No pk means the object was deleted
            return self.publisher_get_admin_changelist_url(obj)
        else:
            return self.publisher_get_detail_admin_url(obj)

    def publisher_get_detail_admin_url(self, obj):
        info = obj._meta.app_label, obj._meta.model_name
        return reverse('admin:{}_{}_change'.format(*info), args=(obj.pk,))

    def publisher_get_admin_changelist_url(self, obj=None):
        info = obj._meta.app_label, obj._meta.model_name
        return reverse('admin:{}_{}_changelist'.format(*info))

    def publisher_get_is_enabled(self, request, obj):
        # This allows subclasses to disable draft-live logic. Returning False
        # here will cause the "published" version in admin to be editable and
        # not show any of the special submit buttons for publishing.
        # Only override this if your app has a setting to disable publishing
        # alltogether.
        return True

    def has_delete_permission(self, request, obj=None):
        if PARLER_IS_INSTALLED:
            # Parler checks with this method for the translation specific delete
            # view as well.
            # We can't add the publisher related methods to the parler
            # translation model. So we short-circut to use the permissions of
            # the shared model instead.
            from parler.models import TranslatedFieldsModel
            if isinstance(obj, TranslatedFieldsModel):
                obj = obj.master
        if obj and obj.pk and obj.publisher_is_published_version:
            if (
                obj.publisher_has_pending_deletion_request and
                self.has_publish_permission(request, obj)
            ):
                return True
            return False
        elif obj and obj.pk and obj.publisher_is_draft_version and obj.publisher_has_pending_changes:
            return False
        return (
            super(PublisherAdminMixinBase, self)
            .has_delete_permission(request, obj)
        )

    def has_publish_permission(self, request, obj):
        # FIXME: prefix this method with 'publisher_' too?
        return True

    def publisher_get_buttons(self, request, obj):
        is_enabled = self.publisher_get_is_enabled(request, obj)

        defaults = get_all_button_defaults()

        has_delete_permission = self.has_delete_permission(request, obj)
        has_change_permission = self.has_change_permission(request, obj)
        has_publish_permission = self.has_publish_permission(request, obj)
        add_mode = not bool(obj)
        buttons = {}
        if (
            not is_enabled and
            obj and obj.pk and
            obj.publisher_is_published_version and
            not obj.publisher_has_pending_changes
        ):
            # This is the case when we've disable the whole draft/live
            # functionality. We just show the default django buttons.
            self._publisher_get_buttons_default(
                buttons=buttons,
                defaults=defaults,
                has_change_permission=has_change_permission,
                has_delete_permission=has_delete_permission,
            )
            return buttons

        if obj and obj.pk and obj.publisher_is_draft_version and has_change_permission:
            buttons['save'] = copy(defaults['save'])
            buttons['save_and_continue'] = copy(defaults['save_and_continue'])

        if (
            obj and obj.pk and obj.publisher_is_draft_version and
            not obj.publisher_is_published_version and
            has_delete_permission
        ):
            # Not published drafts can be deleted the usual way
            buttons['delete'] = copy(defaults['delete'])

        if add_mode:
            self._publisher_get_buttons_default(
                buttons=buttons,
                defaults=defaults,
                has_change_permission=has_change_permission,
                has_delete_permission=has_delete_permission,
            )
        else:
            self._publisher_get_buttons_edit(
                buttons=buttons,
                obj=obj,
                defaults=defaults,
                has_publish_permission=has_publish_permission,
                request=request,
            )
        ordered_buttons = OrderedDict()
        for key in defaults.keys():
            if key not in buttons:
                continue
            ordered_buttons[key] = buttons.pop(key)
        for key, value in buttons.items():
            ordered_buttons[key] = value
        return ordered_buttons

    def _publisher_get_buttons_default(self, buttons, defaults, has_change_permission, has_delete_permission):
        if has_change_permission:
            buttons['save'] = copy(defaults['save'])
            buttons['save_and_continue'] = copy(defaults['save_and_continue'])
        if has_delete_permission:
            buttons['delete'] = copy(defaults['delete'])

    def _publisher_get_buttons_edit(self, buttons, defaults, obj, has_publish_permission, request):
        for action in obj.publisher_available_actions(request.user).values():
            action_name = action['name']
            buttons[action_name] = copy(defaults[action_name])
            buttons[action_name].update(action)
            buttons[action_name]['field_name'] = '_{}'.format(action_name)

        if not has_publish_permission:
            for action_name in ('publish', 'publish_deletion'):
                if action_name in buttons:
                    buttons[action_name]['has_permission'] = False

        # Additional links
        if obj.publisher_is_published_version and obj.publisher_has_pending_changes:
            # Add a link for editing an existing draft
            action_name = 'edit_draft'
            buttons[action_name] = copy(defaults[action_name])
            buttons[action_name]['url'] = self.publisher_get_detail_admin_url(obj.publisher_draft_version)
            buttons[action_name]['has_permission'] = True
        if obj.publisher_is_draft_version:
            # Add a link to go back to live
            action_name = 'show_live'
            buttons[action_name] = copy(defaults[action_name])
            if obj.publisher_has_published_version:
                buttons[action_name]['has_permission'] = True
                buttons[action_name]['url'] = self.publisher_get_detail_admin_url(obj.publisher_published_version)
            else:
                buttons[action_name]['has_permission'] = False
        elif obj.publisher_is_draft_version and not obj.publisher_has_published_version:
            # Add a link to go back to live
            action_name = 'show_live'
            buttons[action_name] = copy(defaults[action_name])
            buttons[action_name]['url'] = self.publisher_get_detail_admin_url(obj.publisher_published_version)
            buttons[action_name]['has_permission'] = True
        if obj.publisher_is_published_version and obj.publisher_has_pending_deletion_request:
            # We're going to take the shortcut and show the regular delete
            # view instead of the publish_deletion action, because that will
            # show the user the impact of the deletion.
            if has_publish_permission:
                buttons.pop('publish_deletion', None)
                buttons['delete'] = copy(defaults['delete'])
        if obj.publisher_is_published_version:
            buttons['cancel'] = copy(defaults['cancel'])
            buttons['cancel']['url'] = self.publisher_get_admin_changelist_url(obj)

    def response_change(self, request, obj):
        """
        Overrides the default response_change to handle all the publisher
        workflow actions. This is intentionally after the save has happened,
        so clicking on "publish" on
        a draft will save current changes in the
        form before publishing.
        """
        if request.POST and '_create_draft' in request.POST:
            if obj.publisher_is_published_version and obj.publisher_has_pending_changes:
                # There already is a draft. Just redirect to it.
                return HttpResponseRedirect(
                    self.publisher_get_detail_admin_url(
                        obj.publisher_draft_versiondraft
                    )
                )
            draft = obj.publisher_create_draft()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(draft))
        elif request.POST and '_discard_draft' in request.POST:
            published = obj.publisher_get_published_version()
            obj.publisher_discard_draft()
            return HttpResponseRedirect(self.publisher_get_detail_or_changelist_url(published))
        elif request.POST and '_publish' in request.POST:
            published = obj.publisher_publish()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(published))
        elif request.POST and '_request_deletion' in request.POST:
            published = obj.publisher_request_deletion()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(published))
        elif request.POST and '_discard_requested_deletion' in request.POST:
            obj.publisher_discard_requested_deletion()
            return HttpResponseRedirect(self.publisher_get_detail_admin_url(obj))
        elif request.POST and '_publish_deletion' in request.POST:
            obj.publisher_publish_deletion()
            return HttpResponseRedirect(self.publisher_get_admin_changelist_url(obj))
        return super(PublisherAdminMixinBase, self).response_change(request, obj)

    def publisher_get_status_field_context(self, obj):
        return {
            'original': obj,
        }

    def publisher_status(self, obj):
        context = self.publisher_get_status_field_context(obj)
        return render_to_string(
            'admin/djangocms_publisher/tools/status_label.html',
            context,
        )
    publisher_status.allow_tags = True
    publisher_status.short_description = ''


def get_all_button_defaults():
    defaults = OrderedDict()
    defaults['cancel'] = {'label': _('Cancel')}
    defaults['create_draft'] = {'label': _('Edit'), 'class': 'default'}
    defaults['edit_draft'] = {'label': _('Edit'), 'class': 'default'}
    defaults['show_live'] = {'label': _('View published version')}
    defaults['discard_draft'] = {'label': _('Discard changes'), 'class': 'danger'}
    defaults['publish'] = {'label': _('Publish'), 'class': 'default'}
    defaults['request_deletion'] = {'label': _('Request deletion')}
    defaults['discard_requested_deletion'] = {'label': _('Discard deletion request')}
    defaults['publish_deletion'] = {'label': _('Delete'), 'class': 'danger'}

    # TODO: Support for "save as new" and "save and add another"
    defaults['save'] = {
        'label': _('Save'),
        'class': 'default',
        'field_name': '_save',
    }
    defaults['delete'] = {
        'deletelink': True,  # Special case in template
    }
    defaults['save_and_continue'] = {
        'label': _('Save and continue editing'),
        'field_name': '_continue',
    }
    for btn in defaults.values():
        btn['has_permission'] = True
    return defaults


class PublisherAdminMixin(PublisherAdminMixinBase):
    change_form_template = 'admin/djangocms_publisher/publisher_change_form.html'


class PublisherParlerAdminMixin(PublisherAdminMixinBase):
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = (
            super(PublisherParlerAdminMixin, self)
            .get_readonly_fields(request, obj=obj)
        )
        if not obj or obj and not obj.publisher_is_published_version:
            return readonly_fields
        readonly_fields = set(readonly_fields)
        readonly_fields |= set(obj._parler_meta.get_translated_fields())
        return list(readonly_fields)

    def get_change_form_base_template(self):
        """
        Determine what the actual `change_form_template` should be.
        """
        from parler.admin import _lazy_select_template_name
        opts = self.model._meta
        app_label = opts.app_label
        return _lazy_select_template_name((
            "admin/{0}/{1}/publisher_hange_form.html".format(app_label, opts.object_name.lower()),
            "admin/{0}/publisher_change_form.html".format(app_label),
            "admin/publisher_change_form.html",
            "admin/djangocms_publisher/publisher_change_form.html",
        ))
