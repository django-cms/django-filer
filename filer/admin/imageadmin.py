from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from ..settings import FILER_IMAGE_MODEL
from ..thumbnail_processors import normalize_subject_location
from ..utils.compatibility import string_concat
from ..utils.loader import load_model
from ..utils.provenance import detect_file_provenance, get_digital_source_type_choices
from .fileadmin import FileAdmin, FileAdminChangeFrom


Image = load_model(FILER_IMAGE_MODEL)


class ImageAdminForm(FileAdminChangeFrom):
    subject_location = forms.CharField(
        max_length=64, required=False,
        label=_('Subject location'),
        help_text=_('Location of the main subject of the scene. '
                    'Format: "x,y".'))

    digital_source_type = forms.ChoiceField(
        required=False,
        label=gettext_lazy('Digital source type'),
        help_text=gettext_lazy(
            'How the image was created, e.g., using generative AI. Detected in the '
            'image\'s metadata on upload. Changing it does not change the uploaded '
            'file, but the thumbnails generated from it.'))

    _upload_provenance = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'digital_source_type' in self.fields:
            self.fields['digital_source_type'].choices = get_digital_source_type_choices(
                self.instance.digital_source_type)

    def clean(self):
        # Upload validators, e.g. strip_exif, may remove the provenance
        # information: detect it on the file as it was uploaded
        upload = self.cleaned_data.get("file")
        if "file" in self.changed_data and upload:
            self._upload_provenance = detect_file_provenance(upload)
        return super().clean()

    def _post_clean(self):
        # Assigning the (sanitized) file to the instance detected its provenance again
        super()._post_clean()
        if self._upload_provenance is not None:
            self.instance._set_provenance(self._upload_provenance)
        if "digital_source_type" in self.changed_data:
            # The user's choice takes precedence, also over a new file's metadata
            self.instance.set_digital_source_type(self.cleaned_data.get("digital_source_type", ""))

    def sidebar_image_ratio(self):
        if self.instance:
            # this is very important. It forces the value to be returned as a
            # string and always with a "." as separator. If the conversion
            # from float to string is done in the template, the locale will
            # be used and in some cases there would be a "," instead of ".".
            # javascript would parse that to an integer.
            return '%.6F' % self.instance.sidebar_image_ratio()
        else:
            return ''

    def _set_previous_subject_location(self, cleaned_data):
        subject_location = self.instance.subject_location
        cleaned_data['subject_location'] = subject_location
        self.data = self.data.copy()
        self.data['subject_location'] = subject_location

    def clean_subject_location(self):
        """
        Validate subject_location preserving last saved value.

        Last valid value of the subject_location field is shown to the user
        for subject location widget to receive valid coordinates on field
        validation errors.
        """
        subject_location = self.cleaned_data['subject_location']
        if not subject_location:
            # if supplied subject location is empty, do not check it
            return subject_location

        # use thumbnail's helper function to check the format
        coordinates = normalize_subject_location(subject_location)

        if not coordinates:
            err_msg = gettext_lazy('Invalid subject location format. ')
            err_code = 'invalid_subject_format'

        elif (
            coordinates[0] > self.instance.width > 0
            or coordinates[1] > self.instance.height > 0
        ):
            err_msg = gettext_lazy(
                'Subject location is outside of the image. ')
            err_code = 'subject_out_of_bounds'
        else:
            return subject_location

        self._set_previous_subject_location(self.cleaned_data)
        raise forms.ValidationError(
            string_concat(
                err_msg,
                gettext_lazy('Your input: "{subject_location}". '.format(
                    subject_location=subject_location)),
                'Previous value is restored.'),
            code=err_code)

    class Meta:
        model = Image
        exclude = ()


class ImageAdmin(FileAdmin):
    change_form_template = 'admin/filer/image/change_form.html'
    form = ImageAdminForm


if FILER_IMAGE_MODEL == 'filer.Image':
    extra_main_fields = ('author', 'default_alt_text', 'default_caption', 'digital_source_type',)
else:
    extra_main_fields = ('default_alt_text', 'default_caption', 'digital_source_type',)

ImageAdmin.fieldsets = ImageAdmin.build_fieldsets(
    extra_main_fields=extra_main_fields,
    extra_fieldsets=(
        (_('Subject location'), {
            'fields': ('subject_location',),
            'classes': ('collapse',),
        }),
    )
)
