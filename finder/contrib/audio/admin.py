from django.contrib import admin
from django.forms.fields import CharField, FloatField
from django.forms.widgets import HiddenInput, TextInput

from entangled.forms import EntangledModelForm

from finder.admin.file import FileAdmin
from finder.contrib.audio.models import AudioFileModel, SAMPLE_DURATION


class AudioForm(EntangledModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
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
        untangled_fields = ['name']

    class Media:
        css = {'all': ['admin/css/forms.css']}


@admin.register(AudioFileModel)
class AudioAdmin(FileAdmin):
    form = AudioForm
    exclude = None
