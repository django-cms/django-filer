# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import warnings

from django import forms
from django.contrib.admin.sites import site
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.template.loader import render_to_string
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from .. import settings as filer_settings
from ..models import File
from ..utils.compatibility import LTE_DJANGO_1_8, reverse, truncate_words
from ..utils.model_label import get_model_label


logger = logging.getLogger(__name__)


class AdminFileWidget(ForeignKeyRawIdWidget):
    choices = None

    def render(self, name, value, attrs=None, renderer=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id', 'id_image_x')
        related_url = None
        if value:
            try:
                file_obj = File.objects.get(pk=value)
                related_url = file_obj.logical_folder.get_admin_directory_listing_url_path()
            except Exception as e:
                # catch exception and manage it. We can re-raise it for debugging
                # purposes and/or just logging it, provided user configured
                # proper logging configuration
                if filer_settings.FILER_ENABLE_LOGGING:
                    logger.error('Error while rendering file widget: %s', e)
                if filer_settings.FILER_DEBUG:
                    raise
        if not related_url:
            related_url = reverse('admin:filer-directory_listing-last')
        params = self.url_parameters()
        params['_pick'] = 'file'
        if params:
            lookup_url = '?' + urlencode(sorted(params.items()))
        else:
            lookup_url = ''
        if 'class' not in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        # rendering the super for ForeignKeyRawIdWidget on purpose here because
        # we only need the input and none of the other stuff that
        # ForeignKeyRawIdWidget adds
        hidden_input = super(ForeignKeyRawIdWidget, self).render(name, value, attrs)
        context = {
            'hidden_input': hidden_input,
            'lookup_url': '%s%s' % (related_url, lookup_url),
            'object': obj,
            'lookup_name': name,
            'id': css_id,
            'admin_icon_delete': (
                'admin/img/icon_deletelink.gif' if LTE_DJANGO_1_8
                else 'admin/img/icon-deletelink.svg'
            ),
        }
        html = render_to_string('admin/filer/widgets/admin_file.html', context)
        return mark_safe(html)

    def label_for_value(self, value):
        obj = self.obj_for_value(value)
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)

    def obj_for_value(self, value):
        if value:
            try:
                key = self.rel.get_related_field().name
                if LTE_DJANGO_1_8:
                    obj = self.rel.to._default_manager.get(**{key: value})
                else:
                    obj = self.rel.model._default_manager.get(**{key: value})
            except ObjectDoesNotExist:
                obj = None
        else:
            obj = None
        return obj

    class Media(object):
        css = {
            'all': [
                'filer/css/admin_filer.css',
            ]
        }
        js = (
            'filer/js/libs/dropzone.min.js',
            'filer/js/addons/dropzone.init.js',
            'filer/js/addons/popup_handling.js',
            'filer/js/addons/widget.js',
        )


class AdminFileFormField(forms.ModelChoiceField):
    widget = AdminFileWidget

    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        kwargs.pop('widget', None)
        super(AdminFileFormField, self).__init__(queryset, widget=self.widget(rel, site), *args, **kwargs)

    def widget_attrs(self, widget):
        widget.required = self.required
        return {}


class FilerFileField(models.ForeignKey):
    default_form_class = AdminFileFormField
    default_model_class = File

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
        super(FilerFileField, self).__init__(**kwargs)

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
        return super(FilerFileField, self).formfield(**defaults)
