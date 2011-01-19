import os
from django.utils.translation import ugettext as _
from django.utils.text import truncate_words
from django.utils import simplejson
from django.db import models
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from sorl.thumbnail.base import ThumbnailException
from filer.settings import FILER_STATICMEDIA_PREFIX
from django.conf import settings as globalsettings
from filer.models import File

class AdminFileWidget(ForeignKeyRawIdWidget):
    choices = None
    def render(self, name, value, attrs=None):
        obj = self.obj_for_value(value)
        css_id = attrs.get('id', 'id_image_x')
        css_id_thumbnail_img = "%s_thumbnail_img" % css_id
        css_id_description_txt = "%s_description_txt" % css_id
        super_attrs = attrs.copy()
        related_url = None
        if value:
            try:
                file = File.objects.get(pk=value)
                related_url = file.logical_folder.get_admin_directory_listing_url_path()
            except Exception,e:
                print e
        if not related_url:
            related_url = reverse('admin:filer-directory_listing-root')
        params = self.url_parameters()
        if params:
            lookup_url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            lookup_url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript looks for this hook.
        # rendering the super for ForeignKeyRawIdWidget on purpose here beacuase
        # we only need the input and none of the other stuff that
        # ForeignKeyRawIdWidget adds
        hidden_input = super(ForeignKeyRawIdWidget, self).render(name, value, attrs)
        filer_static_prefix = FILER_STATICMEDIA_PREFIX
        if not filer_static_prefix[-1] == '/':
            filer_static_prefix += '/'
        context = {
            'hidden_input': hidden_input,
            'lookup_url': '%s%s' % (related_url, lookup_url),
            'thumb_id': css_id_thumbnail_img,
            'span_id': css_id_description_txt,
            'object': obj,
            'lookup_name': name,
            'admin_media_prefix': globalsettings.ADMIN_MEDIA_PREFIX,
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
        js = (FILER_STATICMEDIA_PREFIX+'js/popup_handling.js',)

class AdminFileFormField(forms.ModelChoiceField):
    widget = AdminFileWidget
    def __init__(self, rel, queryset, to_field_name, *args, **kwargs):
        self.rel = rel
        self.queryset = queryset
        self.to_field_name = to_field_name
        self.max_value = None
        self.min_value = None
        other_widget = kwargs.pop('widget', None)
        forms.Field.__init__(self, widget=self.widget(rel), *args, **kwargs)
        
    def widget_attrs(self, widget):
        widget.required = self.required
        return {}


from filer.models import File
class FilerFileField(models.ForeignKey):
    default_form_class = AdminFileFormField
    default_model_class = File
    def __init__(self, **kwargs):
        # we call ForeignKey.__init__ with the Image model as parameter...
        # a FilerImageFiled can only be a ForeignKey to a Image
        return super(FilerFileField,self).__init__(self.default_model_class, **kwargs)
    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        #defaults = {'form_class': ImageFilerImageWidget}
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