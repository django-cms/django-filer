from django.forms.fields import FloatField
from django.forms.widgets import NumberInput
from django.utils.translation import gettext_lazy as _

from entangled.forms import EntangledModelFormMixin

from finder.contrib.video.models import VideoFileModel
from finder.forms.file import FileForm


class VideoFileForm(EntangledModelFormMixin, FileForm):
    sample_start = FloatField(
        label=_("Poster timestamp"),
        widget=NumberInput(attrs={'readonly': 'readonly'}),
        required=False,
    )

    class Meta:
        model = VideoFileModel
        entangled_fields = {'meta_data': ['sample_start']}
        untangled_fields = ['name', 'tags']
