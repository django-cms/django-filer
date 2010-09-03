from django.utils.translation import ugettext as _
from django.utils.text import truncate_words
from django.utils import simplejson
from django.db import models
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.conf import settings
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
        related_url = reverse('admin:filer-directory_listing-root')
        params = self.url_parameters()
        params['select_folder'] = 1
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField' # The JavaScript looks for this hook.
        output = []
        if obj:
            output.append(u'Folder: <span id="%s">%s</span>' % (css_id_description_txt,obj.name))
        else:
            output.append(u'Folder: <span id="%s">none selected</span>' % css_id_description_txt)
        # TODO: "id_" is hard-coded here. This should instead use the correct
        # API to determine the ID dynamically.
        output.append('<a href="%s%s" class="related-lookup" id="lookup_id_%s" onclick="return showRelatedObjectLookupPopup(this);"> ' % \
            (related_url, url, name))
        output.append('<img src="%simg/admin/selector-search.gif" width="16" height="16" alt="%s" /></a>' % (settings.ADMIN_MEDIA_PREFIX, _('Lookup')))
        output.append('</br>')
        #super_attrs = attrs.copy()
        #output.append( super(ForeignKeyRawIdWidget, self).render(name, value, super_attrs) )
        clearid = '%s_clear' % css_id
        output.append('<img id="%s" src="%simg/admin/icon_deletelink.gif" width="10" height="10" alt="%s" title="%s"/>' % (clearid, settings.ADMIN_MEDIA_PREFIX, _('Clear'),  _('Clear')))
        output.append('<br />')
        super_attrs = attrs.copy()
        output.append( super(ForeignKeyRawIdWidget, self).render(name, value, super_attrs) )
        noimgurl = '%sicons/nofile_32x32.png' % FILER_STATICMEDIA_PREFIX
        js = '''<script type="text/javascript">django.jQuery("#%(id)s").hide();
django.jQuery("#%(id)s_clear").click(function(){
    django.jQuery("#%(id)s").removeAttr("value");
    django.jQuery("#%(foldid)s").attr("src", "%(noimg)s");
    django.jQuery("#%(descid)s").html("");
});
django.jQuery(document).ready(function(){
    var plus = django.jQuery("#add_%(id)s");
    if (plus.length){
        plus.remove();
    }
});
</script>'''
        output.append(js % {'id': css_id, 'foldid': css_id_folder,
                            'noimg': noimgurl, 'descid': css_id_description_txt})
        return mark_safe(u''.join(output))
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



class AdminFolderFormField(forms.ModelChoiceField):
    widget = AdminFolderWidget 
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

from filer.models import Folder
class FilerFolderField(models.ForeignKey):
    default_form_class = AdminFolderFormField
    default_model_class = Folder
    def __init__(self, **kwargs):
        return super(FilerFolderField,self).__init__(Folder, **kwargs)
    def formfield(self, **kwargs):
        # This is a fairly standard way to set up some defaults
        # while letting the caller override them.
        #defaults = {'form_class': FilerFolderWidget}
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
