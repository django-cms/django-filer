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
            'fields': ('conversion_status', 'height','width',
                       'conversion_output',),
            'classes': ('collapse',),
        })
    )
    
    def render_change_form(self, request, context, *args, **kwargs):
        video = Video.objects.get(pk=context['object_id'])
        context['adminform'].form.fields['width'].help_text = _('Uploaded video width %s px') % video.original_width
        context['adminform'].form.fields['height'].help_text = _('Uploaded video height %s px') % video.original_height
        return super(VideoAdmin, self).render_change_form(request, context, args, kwargs)
