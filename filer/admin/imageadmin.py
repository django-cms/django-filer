from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin.util import unquote, flatten_fieldsets, get_deleted_objects, model_ngettext, model_format_dict
from django.utils.translation import ugettext  as _
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib import admin
from django import forms
from django.db.models import Q
from filer.admin.permissions import PrimitivePermissionAwareModelAdmin
from filer.admin.fileadmin import FileAdmin
from filer.models import Folder, FolderRoot, UnfiledImages, \
                            ImagesWithMissingData, File, Image
from filer.admin.tools import *
from filer.models import tools

from django.conf import settings

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
            settings.MEDIA_URL + 'filer/js/raphael.js',
            settings.MEDIA_URL + 'filer/js/focal_point.js',
        )

#ModelAdmins
class ImageAdmin(FileAdmin):
    
    form = ImageAdminFrom
    fieldsets = (
        FileAdmin.fieldsets[0],
        (None, {
            'fields': ('subject_location',),
            'classes': ('hide',),
        }),
        FileAdmin.fieldsets[1],
    )
