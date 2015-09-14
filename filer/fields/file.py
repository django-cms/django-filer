# -*- coding: utf-8 -*-

import warnings

from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.contrib.admin.sites import site
from django.core.urlresolvers import reverse
from django.db import models
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ungettext_lazy


from filer.utils.compatibility import truncate_words
from filer.utils.model_label import get_model_label
from filer.models import File
from filer.validators import FileMimetypeValidator
from filer import settings as filer_settings

import logging
logger = logging.getLogger(__name__)


class AdminFileWidget(ForeignKeyRawIdWidget):
    template = 'admin/filer/widgets/admin_file.html'
    choices = None

    def __init__(self, rel, site, *args, **kwargs):
        self.file_lookup_enabled = kwargs.pop('file_lookup_enabled', True)
        self.direct_upload_enabled = kwargs.pop('direct_upload_enabled', True)
        self.folder_key = kwargs.pop('folder_key', None)
        super(AdminFileWidget, self).__init__(rel, site, *args, **kwargs)

    def get_context(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id', 'id_image_x')
        css_id_thumbnail_img = "%s_thumbnail_img" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
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

        if self.folder_key:
            related_url = reverse(
                'admin:filer-directory_listing_by_key',
                kwargs={'folder_key': self.folder_key}
            )
        elif not related_url:
            related_url = reverse('admin:filer-directory_listing-last')
        params = self.url_parameters()
        if params:
            lookup_url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in list(params.items())])
        else:
            lookup_url = ''
        if 'class' not in attrs:
            # The JavaScript looks for this hook.
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        # rendering the super for ForeignKeyRawIdWidget on purpose here because
        # we only need the input and none of the other stuff that
        # ForeignKeyRawIdWidget adds
        attrs['type'] = 'hidden'
        hidden_input = super(ForeignKeyRawIdWidget, self).render(name, value, attrs)
        context = {
            'hidden_input': hidden_input,
            'lookup_url': '%s%s' % (related_url, lookup_url),
            'thumb_id': css_id_thumbnail_img,
            'span_id': css_id_description_txt,
            'object': obj,
            'lookup_name': name,
            'clear_id': '%s_clear' % css_id,
            'id': css_id,
            'file_lookup_enabled': self.file_lookup_enabled,
            'direct_upload_enabled': self.direct_upload_enabled,
        }
        related_field = '%s.%s.%s' % (
            self.rel.field.model._meta.app_label,
            self.rel.field.model.__name__,
            self.rel.field.name,
        )
        direct_upload_url = reverse('admin:filer-ajax_upload',
                                    kwargs={'related_field': related_field,
                                            'folder_key': self.folder_key})
        context.update({
            'direct_upload_related_field': related_field,
            'folder_key': self.folder_key or 'no_folder',
            'direct_upload_url': direct_upload_url,
        })
        return context

    def render(self, name, value, attrs=None):
        context = self.get_context(name, value, attrs)
        html = render_to_string(self.template, context)
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

    @property
    def media(self):
        kwargs = {
            'css': {
                'all': ('css/admin_style.css',),
            },
            'js': [
                'filer/js/libs/jquery.min.js',
                'filer/js/addons/widget.js',
            ],
        }
        if self.direct_upload_enabled:
            kwargs['js'] += [
                'filer/js/libs/dropzone.min.js',
                'filer/js/addons/dropzone.init.js',
            ]
        if self.file_lookup_enabled:
            kwargs['js'].append('filer/js/addons/popup_handling.js')
        return super(AdminFileWidget, self).media + forms.Media(**kwargs)


class AdminFileFormField(forms.ModelChoiceField):
    widget = AdminFileWidget

    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        kwargs.pop('widget', None)
        widgetkwargs = {
            'file_lookup_enabled': kwargs.pop('file_lookup_enabled', True),
            'direct_upload_enabled': kwargs.pop('direct_upload_enabled', False),
            'folder_key': kwargs.pop('folder_key', None),
        }

        super(AdminFileFormField, self).__init__(
            queryset,
            widget=self.widget(rel, site, **widgetkwargs),
            *args, **kwargs
        )

        if not self.help_text:
            validators = self.validators + self.rel.field.validators
            for validator in validators:
                if isinstance(validator, FileMimetypeValidator):
                    if len(validator.mimetypes) > 1:
                        mimetypes = _('%s" and "%s') % (
                            '", "'.join(validator.mimetypes[0:-1]),
                            validator.mimetypes[-1]
                        )
                    else:
                        mimetypes = validator.mimetypes[0]
                    self.help_text = ungettext_lazy(
                        'Only files of type "%(mimetypes)s" are allowed',
                        'Only files of types "%(mimetypes)s" are allowed',
                        len(validator.mimetypes)
                    ) % {
                        'mimetypes': mimetypes
                    }
                    break

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
        default_keys = (
            'form_class', 'file_lookup_enabled',
            'direct_upload_enabled', 'folder_key'
        )
        self.default_formfield_kwargs = {'form_class': self.default_form_class, }
        for key in default_keys:
            default_key = 'default_%s' % key
            if default_key in kwargs:
                self.default_formfield_kwargs[key] = kwargs.pop(default_key)
        super(FilerFileField, self).__init__(**kwargs)

    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        defaults = {'rel': self.rel, }
        defaults.update(self.default_formfield_kwargs)
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
