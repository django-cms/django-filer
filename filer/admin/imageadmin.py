# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django import forms
from django.utils.translation import ugettext as _

from ..models import Image
from ..thumbnail_processors import normalize_subject_location

from .fileadmin import FileAdmin


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
            return '%.6F' % self.instance.sidebar_image_ratio()
        else:
            return ''

    def clean_subject_location(self):
        subject_location = self.cleaned_data['subject_location']
        if not subject_location:
            # if supplied subject location is empty, do not check it
            return subject_location

        # use thumbnail's helper function to check the format
        coordinates = normalize_subject_location(subject_location)
        if not coordinates:
            raise forms.ValidationError(
                _('Invalid subject location format'),
                code='invalid_subject_format')

        if (coordinates[0] > self.instance.image.width or
                coordinates[1] > self.instance.image.height):
            raise forms.ValidationError(
                _('Subject location is outside of the image'),
                code='subject_out_of_bounds')

        return subject_location

    class Meta(object):
        model = Image
        exclude = ()

    class Media(object):
        css = {
            # 'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
        }
        js = (

        )


class ImageAdmin(FileAdmin):
    form = ImageAdminForm


ImageAdmin.fieldsets = ImageAdmin.build_fieldsets(
    extra_main_fields=('author', 'default_alt_text', 'default_caption',),
    extra_fieldsets=(
        ('Subject Location', {
            'fields': ('subject_location',),
            'classes': ('collapse',),
        }),
    )
)
