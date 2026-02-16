from django.forms.fields import FloatField
from django.forms.widgets import HiddenInput

from entangled.forms import EntangledModelFormMixin

from finder.contrib.audio.models import AudioFileModel, SAMPLE_DURATION
from finder.forms.file import FileForm


class AudioFileForm(EntangledModelFormMixin, FileForm):
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
        untangled_fields = ['name', 'tags']
