#-*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext  as _
from filer import settings as filer_settings
from filer.admin.fileadmin import FileAdmin
from filer.models import Video


class VideoAdminFrom(forms.ModelForm):
    class Meta:
        model = Video

    #class Media:
        #css = {
            ##'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
        #}
        #js = (
            #filer_settings.FILER_STATICMEDIA_PREFIX + 'js/raphael.js',
            #filer_settings.FILER_STATICMEDIA_PREFIX + 'js/focal_point.js',
        #)


class VideoAdmin(FileAdmin):
    form = VideoAdminFrom
    fieldsets = (
        FileAdmin.fieldsets[0],
        (_('Advanced'), {
            'fields': ('default_alt_text', 'default_caption',
                       'author', 'file', 'sha1',),
            'classes': ('collapse',),
        }),
        (_('Conversion'), {
            'fields': ('conversion_status', 'conversion_output',),
            'classes': ('collapse',),
        })
    )
