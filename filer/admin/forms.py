from django import forms
from django.contrib.admin import widgets
from django.contrib.admin.helpers import AdminForm
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _

from ..models import ThumbnailOption
from ..utils.files import get_valid_filename


class WithFieldsetMixin:
    def get_fieldsets(self):
        return getattr(self, "fieldsets", [
            (None, {"fields": [field for field in self.fields]})
        ])

    def admin_form(self):
        "Returns a class contains the Admin fieldset to show form as admin form"
        return AdminForm(self, self.get_fieldsets(), {})


class CopyFilesAndFoldersForm(forms.Form):
    suffix = forms.CharField(required=False, help_text=_("Suffix which will be appended to filenames of copied files."))
    # TODO: We have to find a way to overwrite files with different storage backends first.
    # overwrite_files = forms.BooleanField(required=False, help_text=_("Overwrite a file if there already exists a file with the same filename?"))

    def clean_suffix(self):
        valid = get_valid_filename(self.cleaned_data['suffix']) if self.cleaned_data['suffix'] else ""
        if valid != self.cleaned_data['suffix']:
            raise forms.ValidationError(_('Suffix should be a valid, simple and lowercase filename part, like "%(valid)s".') % {'valid': valid})
        return self.cleaned_data['suffix']


class RenameFilesForm(WithFieldsetMixin, forms.Form):
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


class ResizeImagesForm(WithFieldsetMixin, forms.Form):
    fieldsets = ((None, {"fields": (
        "thumbnail_option",
        ("width", "height"),
        ("crop", "upscale"))}),)

    thumbnail_option = models.ForeignKey(
        ThumbnailOption,
        null=True,
        blank=True,
        verbose_name=_("thumbnail option"),
        on_delete=models.CASCADE,
    ).formfield()

    width = models.PositiveIntegerField(_("width"), null=True, blank=True).formfield(widget=widgets.AdminIntegerFieldWidget)
    height = models.PositiveIntegerField(_("height"), null=True, blank=True).formfield(widget=widgets.AdminIntegerFieldWidget)
    crop = models.BooleanField(_("crop"), default=True).formfield()
    upscale = models.BooleanField(_("upscale"), default=True).formfield()

    def clean(self):
        if not (self.cleaned_data.get('thumbnail_option') or ((self.cleaned_data.get('width') or 0) + (self.cleaned_data.get('height') or 0))):
            raise ValidationError(_('Thumbnail option or resize parameters must be choosen.'))
        return self.cleaned_data
