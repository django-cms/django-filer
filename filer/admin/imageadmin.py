#-*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext  as _
from django.shortcuts import render
from django.template import RequestContext
from django.http import Http404
from django.urls import re_path
from filer import settings as filer_settings, settings
from filer.admin.fileadmin import FileAdmin
from filer.models import Image
from filer.views import (popup_status, selectfolder_status)


class ImageAdminForm(forms.ModelForm):
    subject_location = forms.CharField(
                    max_length=64, required=False,
                    label=_('Subject location'),
                    help_text=_('Location of the main subject of the scene.'))

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
        exclude = ()


class ImageAdmin(FileAdmin):
    form = ImageAdminForm

    def get_urls(self):
        from django.conf.urls import url
        urls = super(ImageAdmin, self).get_urls()
        url_patterns = [
            re_path(r'^(?P<file_id>\d+)/full_size_preview/$',
                self.admin_site.admin_view(self.full_size_preview),
                name='filer-image-preview'),
        ]
        url_patterns.extend(urls)
        return url_patterns

    def full_size_preview(self, request, file_id):
        try:
            image = Image.objects.get(id=file_id)
        except Image.DoesNotExist:
            raise Http404

        return render(request, 'admin/filer/image/full_size_preview.html', {
                'image': image,
                'current_site': request.GET.get('current_site', None),
                'is_popup': popup_status(request),
                'select_folder': selectfolder_status(request),
                })

ImageAdmin.fieldsets = ImageAdmin.build_fieldsets(
    extra_main_fields=('default_alt_text', 'default_caption', 'default_credit'),
    extra_fieldsets=()
)
