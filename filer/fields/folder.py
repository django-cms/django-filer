# -*- coding: utf-8 -*-
from __future__ import absolute_import

import warnings

from django import forms
from django.contrib.admin.sites import site
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.template.loader import render_to_string
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from ..models import Folder
from ..utils.compatibility import LTE_DJANGO_1_8, reverse, truncate_words
from ..utils.model_label import get_model_label


class AdminFolderWidget(ForeignKeyRawIdWidget):
    choices = None
    input_type = 'hidden'
    is_hidden = False

    def render(self, name, value, attrs=None, renderer=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id')
        css_id_folder = "%s_folder" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
        if attrs is None:
            attrs = {}
        related_url = None
        if value:
            try:
                folder = Folder.objects.get(pk=value)
                related_url = folder.get_admin_directory_listing_url_path()
            except Exception:
                pass
        if not related_url:
            related_url = reverse('admin:filer-directory_listing-last')
        params = self.url_parameters()
        params['_pick'] = 'folder'
        if params:
            url = '?' + urlencode(sorted(params.items()))
        else:
            url = ''
        if 'class' not in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        super_attrs = attrs.copy()
        hidden_input = super(ForeignKeyRawIdWidget, self).render(name, value, super_attrs)

        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        context = {
            'hidden_input': hidden_input,
            'lookup_url': '%s%s' % (related_url, url),
            'lookup_name': name,
            'span_id': css_id_description_txt,
            'object': obj,
            'clear_id': '%s_clear' % css_id,
            'descid': css_id_description_txt,
            'noimg': 'filer/icons/nofile_32x32.png',
            'foldid': css_id_folder,
            'id': css_id,
        }
        html = render_to_string('admin/filer/widgets/admin_folder.html', context)
        return mark_safe(html)

    def label_for_value(self, value):
        obj = self.obj_for_value(value)
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)

    def obj_for_value(self, value):
        try:
            key = self.rel.get_related_field().name
            if LTE_DJANGO_1_8:
                obj = self.rel.to._default_manager.get(**{key: value})
            else:
                obj = self.rel.model._default_manager.get(**{key: value})
        except ObjectDoesNotExist:
            obj = None
        return obj

    class Media(object):
        js = (
            'filer/js/addons/popup_handling.js',
        )


class AdminFolderFormField(forms.ModelChoiceField):
    widget = AdminFolderWidget

    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.limit_choices_to = kwargs.pop('limit_choices_to', None)
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        kwargs.pop('widget', None)
        forms.Field.__init__(self, widget=self.widget(rel, site), *args, **kwargs)

    def widget_attrs(self, widget):
        widget.required = self.required
        return {}


class FilerFolderField(models.ForeignKey):
    default_form_class = AdminFolderFormField
    default_model_class = Folder

    def __init__(self, **kwargs):
        # We hard-code the `to` argument for ForeignKey.__init__
        dfl = get_model_label(self.default_model_class)
        if "to" in kwargs.keys():  # pragma: no cover
            old_to = get_model_label(kwargs.pop("to"))
            if old_to != dfl:
                msg = "%s can only be a ForeignKey to %s; %s passed" % (
                    self.__class__.__name__, dfl, old_to
                )
                warnings.warn(msg, SyntaxWarning)
        kwargs['to'] = dfl
        super(FilerFolderField, self).__init__(**kwargs)

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {
            'form_class': self.default_form_class,
        }
        try:
            defaults['rel'] = self.remote_field
        except AttributeError:
            defaults['rel'] = self.rel
        defaults.update(kwargs)
        return super(FilerFolderField, self).formfield(**defaults)
