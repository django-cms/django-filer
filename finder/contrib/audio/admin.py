from django.contrib import admin
from django.forms.fields import FloatField
from django.forms.widgets import HiddenInput

from finder.admin.file import FileAdmin, FileModelForm
from finder.contrib.audio.models import AudioFileModel, SAMPLE_DURATION


class AudioForm(FileModelForm):
    sample_start = FloatField(
        widget=HiddenInput(),
        initial=0,
    )
    sample_duration = FloatField(
        widget=HiddenInput(),
        initial=SAMPLE_DURATION,
    )

    class Meta:
        model = AudioFileModel
        entangled_fields = {'meta_data': ['sample_start', 'sample_duration']}
        untangled_fields = ['name', 'labels']

    class Media:
        css = {'all': ['admin/css/forms.css']}


@admin.register(AudioFileModel)
class AudioAdmin(FileAdmin):
    form = AudioForm
    exclude = None

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        settings.update(
            replacing_mime_type=settings['file_mime_type'],
        )
        return settings
