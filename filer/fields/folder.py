#-*- coding: utf-8 -*-
from django.template.loader import render_to_string
import inspect
from django import forms
from django.conf import settings
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.contrib.admin.sites import site
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.safestring import mark_safe
from filer.utils.compatibility import truncate_words
from django.utils.translation import ugettext as _
from filer.models import Folder
from filer.settings import FILER_STATICMEDIA_PREFIX


class AdminFolderWidget(ForeignKeyRawIdWidget):
    choices = None
    input_type = 'hidden'
    is_hidden = True

    def render(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id')
        css_id_folder = "%s_folder" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
        required = self.attrs
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
        params['select_folder'] = 1
        if params:
            url = '?' + '&amp;'.join(
                            ['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not 'class' in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        super_attrs = attrs.copy()
        hidden_input = super(ForeignKeyRawIdWidget, self).render(
                                                    name, value, super_attrs)

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
            'noimg': '%sicons/nofile_32x32.png' % FILER_STATICMEDIA_PREFIX,
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
            obj = self.rel.to._default_manager.get(**{key: value})
        except:
            obj = None
        return obj

    class Media:
        js = (FILER_STATICMEDIA_PREFIX + 'js/popup_handling.js',)


class AdminFolderFormField(forms.ModelChoiceField):
    widget = AdminFolderWidget

    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        kwargs.pop('widget', None)
        if 'admin_site' in inspect.getargspec(self.widget.__init__)[0]: # Django 1.4
            widget_instance = self.widget(rel, site)
        else: # Django <= 1.3
            widget_instance = self.widget(rel)
        forms.Field.__init__(self, widget=widget_instance, *args, **kwargs)

    def widget_attrs(self, widget):
        widget.required = self.required
        return {}


class FilerFolderField(models.ForeignKey):
    default_form_class = AdminFolderFormField
    default_model_class = Folder

    def __init__(self, **kwargs):
        return super(FilerFolderField, self).__init__(Folder, **kwargs)

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {
            'form_class': self.default_form_class,
            'rel': self.rel,
        }
        defaults.update(kwargs)
        return super(FilerFolderField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect ourselves, since we inherit.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.related.ForeignKey"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)
