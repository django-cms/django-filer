#-*- coding: utf-8 -*-
import inspect
from django import forms
from django.conf import settings as globalsettings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.contrib.admin.sites import site
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from filer.utils.compatibility import truncate_words
from filer.models import File
from filer import settings as filer_settings

import logging
logger = logging.getLogger(__name__)

class AdminFileWidget(ForeignKeyRawIdWidget):
    choices = None

    def render(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id', 'id_image_x')
        css_id_thumbnail_img = "%s_thumbnail_img" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
        related_url = None
        if value:
            try:
                file_obj = File.objects.get(pk=value)
                related_url = file_obj.logical_folder.\
                                get_admin_directory_listing_url_path()
            except Exception,e:
                # catch exception and manage it. We can re-raise it for debugging
                # purposes and/or just logging it, provided user configured
                # proper logging configuration
                if filer_settings.FILER_ENABLE_LOGGING:
                    logger.error('Error while rendering file widget: %s',e)
                if filer_settings.FILER_DEBUG:
                    raise
        if not related_url:
            related_url = reverse('admin:filer-directory_listing-last')
        params = self.url_parameters()
        if params:
            lookup_url = '?' + '&amp;'.join(
                                ['%s=%s' % (k, v) for k, v in params.items()])
        else:
            lookup_url = ''
        if not 'class' in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        # rendering the super for ForeignKeyRawIdWidget on purpose here because
        # we only need the input and none of the other stuff that
        # ForeignKeyRawIdWidget adds
        hidden_input = super(ForeignKeyRawIdWidget, self).render(
                                                            name, value, attrs)
        filer_static_prefix = filer_settings.FILER_STATICMEDIA_PREFIX
        if not filer_static_prefix[-1] == '/':
            filer_static_prefix += '/'
        context = {
            'hidden_input': hidden_input,
            'lookup_url': '%s%s' % (related_url, lookup_url),
            'thumb_id': css_id_thumbnail_img,
            'span_id': css_id_description_txt,
            'object': obj,
            'lookup_name': name,
            'filer_static_prefix': filer_static_prefix,
            'clear_id': '%s_clear' % css_id,
            'id': css_id,
        }
        html = render_to_string('admin/filer/widgets/admin_file.html', context)
        return mark_safe(html)

    def label_for_value(self, value):
        obj = self.obj_for_value(value)
        return '&nbsp;<strong>%s</strong>' % truncate_words(obj, 14)

    def obj_for_value(self, value):
        try:
            key = self.rel.get_related_field().name
            obj = self.rel.to._default_manager.get(**{key: value})
        except:
            obj = None
        return obj

    class Media:
        js = (filer_settings.FILER_STATICMEDIA_PREFIX + 'js/popup_handling.js',)


class AdminFileFormField(forms.ModelChoiceField):
    widget = AdminFileWidget

    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        other_widget = kwargs.pop('widget', None)
        if 'admin_site' in inspect.getargspec(self.widget.__init__)[0]: # Django 1.4
            widget_instance = self.widget(rel, site)
        else: # Django <= 1.3
            widget_instance = self.widget(rel)
        forms.Field.__init__(self, widget=widget_instance, *args, **kwargs)

    def widget_attrs(self, widget):
        widget.required = self.required
        return {}


class FilerFileField(models.ForeignKey):
    default_form_class = AdminFileFormField
    default_model_class = File

    def __init__(self, **kwargs):
        # we call ForeignKey.__init__ with the Image model as parameter...
        # a FilerImageFiled can only be a ForeignKey to a Image
        return super(FilerFileField, self).__init__(
            self.default_model_class, **kwargs)

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {
            'form_class': self.default_form_class,
            'rel': self.rel,
        }
        defaults.update(kwargs)
        return super(FilerFileField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.related.ForeignKey"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)
