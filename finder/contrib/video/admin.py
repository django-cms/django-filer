from django.contrib import admin
from django.forms.fields import CharField, FloatField
from django.forms.widgets import TextInput, NumberInput
from django.utils.translation import gettext_lazy as _

from entangled.forms import EntangledModelForm

from finder.admin.file import FileAdmin
from finder.contrib.video.models import VideoFileModel


class VideoForm(EntangledModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
    sample_start = FloatField(
        label=_("Poster timestamp"),
        widget=NumberInput(attrs={'readonly': 'readonly'}),
        required=False,
    )

    class Meta:
        model = VideoFileModel
        entangled_fields = {'meta_data': ['sample_start']}
        untangled_fields = ['name']

    class Media:
        css = {'all': ['admin/css/forms.css']}


@admin.register(VideoFileModel)
class VideoAdmin(FileAdmin):
    form = VideoForm
    exclude = None

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        settings.update(
            replacing_mime_type=settings['file_mime_type'],
        )
        return settings
