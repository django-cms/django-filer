# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django import forms
from django.conf import settings
from django.contrib.admin import widgets
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext as _

from ..models import ThumbnailOption
from ..utils.files import get_valid_filename


class AsPWithHelpMixin(object):
    def as_p_with_help(self):
        "Returns this form rendered as HTML <p>s with help text formated for admin."
        return self._html_output(
            normal_row='<p%(html_class_attr)s>%(label)s %(field)s</p>%(help_text)s',
            error_row='%s',
            row_ender='</p>',
            help_text_html='<p class="help">%s</p>',
            errors_on_separate_row=True)


class CopyFilesAndFoldersForm(forms.Form, AsPWithHelpMixin):
    suffix = forms.CharField(required=False, help_text=_("Suffix which will be appended to filenames of copied files."))
    # TODO: We have to find a way to overwrite files with different storage backends first.
    # overwrite_files = forms.BooleanField(required=False, help_text=_("Overwrite a file if there already exists a file with the same filename?"))

    def clean_suffix(self):
        valid = get_valid_filename(self.cleaned_data['suffix'])
        if valid != self.cleaned_data['suffix']:
            raise forms.ValidationError(_('Suffix should be a valid, simple and lowercase filename part, like "%(valid)s".') % {'valid': valid})
        return self.cleaned_data['suffix']


class RenameFilesForm(forms.Form, AsPWithHelpMixin):
    rename_format = forms.CharField(required=True)

    def clean_rename_format(self):
        try:
            self.cleaned_data['rename_format'] % {
                'original_filename': 'filename',
                'original_basename': 'basename',
                'original_extension': 'ext',
                'current_filename': 'filename',
                'current_basename': 'basename',
                'current_extension': 'ext',
                'current_folder': 'folder',
                'counter': 42,
                'global_counter': 42,
            }
        except KeyError as e:
            raise forms.ValidationError(_('Unknown rename format value key "%(key)s".') % {'key': e.args[0]})
        except Exception as e:
            raise forms.ValidationError(_('Invalid rename format: %(error)s.') % {'error': e})
        return self.cleaned_data['rename_format']


class ResizeImagesForm(forms.Form, AsPWithHelpMixin):
    if 'cmsplugin_filer_image' in settings.INSTALLED_APPS:
        thumbnail_option = models.ForeignKey(ThumbnailOption, null=True, blank=True, verbose_name=_("thumbnail option")).formfield()
    width = models.PositiveIntegerField(_("width"), null=True, blank=True).formfield(widget=widgets.AdminIntegerFieldWidget)
    height = models.PositiveIntegerField(_("height"), null=True, blank=True).formfield(widget=widgets.AdminIntegerFieldWidget)
    crop = models.BooleanField(_("crop"), default=True).formfield()
    upscale = models.BooleanField(_("upscale"), default=True).formfield()

    def clean(self):
        if not (self.cleaned_data.get('thumbnail_option') or ((self.cleaned_data.get('width') or 0) + (self.cleaned_data.get('height') or 0))):
            if 'cmsplugin_filer_image' in settings.INSTALLED_APPS:
                raise ValidationError(_('Thumbnail option or resize parameters must be choosen.'))
            else:
                raise ValidationError(_('Resize parameters must be choosen.'))
        return self.cleaned_data
