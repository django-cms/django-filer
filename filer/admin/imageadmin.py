from django.utils.translation import ugettext  as _
from django import forms
from filer.admin.fileadmin import FileAdmin
from filer.models import Image

from django.conf import settings
from filer import settings as filer_settings

# forms
class ImageAdminFrom(forms.ModelForm):
    subject_location = forms.CharField(max_length=64, required=False, label=_('Subject location'), help_text=_('Location of the main subject of the scene.'))
    
    def sidebar_image_ratio(self):
        if self.instance:
            # this is very important. It forces the value to be returned as a
            # string and always with a "." as seperator. If the conversion
            # from float to string is done in the template, the locale will
            # be used and in some cases there would be a "," instead of ".".
            # javascript would parse that to an integer.
            return  "%.6F" % self.instance.sidebar_image_ratio()
        else:
            return ''
    
    class Meta:
        model = Image
    class Media:
        css = {
            #'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
        }
        js = (
            filer_settings.FILER_STATICMEDIA_PREFIX + 'js/raphael.js',
            filer_settings.FILER_STATICMEDIA_PREFIX + 'js/focal_point.js',
        )

#ModelAdmins
class ImageAdmin(FileAdmin):
    
    form = ImageAdminFrom
    fieldsets = (
        FileAdmin.fieldsets[0],
        FileAdmin.fieldsets[1],
        FileAdmin.fieldsets[2],
        (_('Subject Location'), {
            'fields': ('subject_location',),
            'classes': ('collapse',),
        }),
    )
