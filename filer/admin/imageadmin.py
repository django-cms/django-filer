from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin.util import unquote, flatten_fieldsets, get_deleted_objects, model_ngettext, model_format_dict
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
    subject_location = forms.CharField(max_length=64, required=False)
    
    def sidebar_image_ratio(self):
        if self.instance:
            return self.instance.sidebar_image_ratio()
        else:
            return ''
    
    class Meta:
        model = Image
    class Media:
        css = {
            #'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
        }
        js = (
            settings.MEDIA_URL + 'filer/js/jquery-1.3.2.min.js',
            settings.MEDIA_URL + 'filer/js/raphael.js',
            settings.MEDIA_URL + 'filer/js/focal_point.js',
        )

#ModelAdmins
class ImageAdmin(FileAdmin):
    
    form = ImageAdminFrom
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', )
        }),
        (None, {
            'fields': ('subject_location',),
            'classes': ('hide',),
        }),
    )
    #fieldsets = (
    #    (None, {
    #        'fields': ('name', 'owner',)#'contact',
    #    }),
    #)
    #class Media:
    #    css = {
    #        'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
    #    }
    #    js = (
    #        settings.MEDIA_URL + 'filer/js/jquery-1.3.2.min.js',
    #        settings.MEDIA_URL + 'filer/js/raphael.js',
    #        settings.MEDIA_URL + 'filer/js/focal_point.js',
    #    )
