#-*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext  as _
from filer import settings as filer_settings
from filer.admin.fileadmin import FileAdmin
from filer.models import Video


class VideoAdminForm(forms.ModelForm):
    class Meta:
        model = Video


class VideoAdmin(FileAdmin):
    form = VideoAdminForm
    fieldsets = (
        FileAdmin.fieldsets[0],
        (_('Advanced'), {
            'fields': ('default_alt_text', 'default_caption',
                       'author', 'file', 'sha1',),
            'classes': ('collapse',),
        }),
        (_('Conversion'), {
            'fields': ('conversion_status', 'original_height','original_width','height','width',
                       'conversion_output',),
            'classes': ('collapse',),
        })
    )
    readonly_fields = ('original_height','original_width')
