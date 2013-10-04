#-*- coding: utf-8 -*-
from django import forms
from django.utils.translation import ugettext  as _
from filer import settings as filer_settings, settings
from filer.admin.fileadmin import FileAdmin
from filer.models import Image


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


class ImageAdmin(FileAdmin):
    form = ImageAdminForm


ImageAdmin.fieldsets = ImageAdmin.build_fieldsets(
    extra_main_fields=('default_alt_text', 'default_caption', 'default_credit'),
    extra_fieldsets=()
)
