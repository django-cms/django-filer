from django.contrib import admin
from django.forms.fields import CharField, IntegerField
from django.forms.widgets import HiddenInput, TextInput

from entangled.forms import EntangledModelForm

from finder.admin.file import FileAdmin
from finder.contrib.video.models import VideoFileModel


class VideoForm(EntangledModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
    poster_frame = IntegerField(
        widget=HiddenInput(),
        initial=0,
    )

    class Meta:
        model = VideoFileModel
        entangled_fields = {'meta_data': ['poster_frame']}
        untangled_fields = ['name']

    class Media:
        css = {'all': ['admin/css/forms.css']}


@admin.register(VideoFileModel)
class VideoAdmin(FileAdmin):
    form = VideoForm
    exclude = None
