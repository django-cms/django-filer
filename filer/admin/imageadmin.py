from django import forms
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from ..settings import FILER_IMAGE_MODEL
from ..thumbnail_processors import normalize_subject_location
from ..utils.compatibility import string_concat
from ..utils.loader import load_model
from .fileadmin import FileAdmin


Image = load_model(FILER_IMAGE_MODEL)


class ImageAdminForm(forms.ModelForm):
    subject_location = forms.CharField(
        max_length=64, required=False,
        label=_('Subject location'),
        help_text=_('Location of the main subject of the scene. '
                    'Format: "x,y".'))

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
        cleaned_data = super().clean()
        subject_location = cleaned_data['subject_location']
        if not subject_location:
            # if supplied subject location is empty, do not check it
            return subject_location

        # use thumbnail's helper function to check the format
        coordinates = normalize_subject_location(subject_location)

        if not coordinates:
            err_msg = gettext_lazy('Invalid subject location format. ')
            err_code = 'invalid_subject_format'

        elif (
            coordinates[0] > self.instance.width
            or coordinates[1] > self.instance.height
        ):
            err_msg = gettext_lazy(
                'Subject location is outside of the image. ')
            err_code = 'subject_out_of_bounds'
        else:
            return subject_location

        self._set_previous_subject_location(cleaned_data)
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

    class Media:
        css = {
            # 'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
        }
        js = (

        )


class ImageAdmin(FileAdmin):
    change_form_template = 'admin/filer/image/change_form.html'
    form = ImageAdminForm


if FILER_IMAGE_MODEL == 'filer.Image':
    extra_main_fields = ('author', 'default_alt_text', 'default_caption',)
else:
    extra_main_fields = ('default_alt_text', 'default_caption',)

ImageAdmin.fieldsets = ImageAdmin.build_fieldsets(
    extra_main_fields=extra_main_fields,
    extra_fieldsets=(
        (_('Subject location'), {
            'fields': ('subject_location',),
            'classes': ('collapse',),
        }),
    )
)
