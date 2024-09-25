from django.contrib import admin
from django.forms.fields import FloatField
from django.forms.widgets import NumberInput
from django.utils.translation import gettext_lazy as _

from finder.admin.file import FileAdmin, FileModelForm
from finder.contrib.video.models import VideoFileModel


class VideoForm(FileModelForm):
    sample_start = FloatField(
        label=_("Poster timestamp"),
        widget=NumberInput(attrs={'readonly': 'readonly'}),
        required=False,
    )

    class Meta:
        model = VideoFileModel
        entangled_fields = {'meta_data': ['sample_start']}
        untangled_fields = ['name', 'labels']

    class Media:
        css = {'all': ['admin/css/forms.css']}


@admin.register(VideoFileModel)
class VideoAdmin(FileAdmin):
    form = VideoForm

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(
            react_component='Video',
            replace_file= True,
            download_file=True,
        )
        return settings

    def get_folderitem_settings(self, request, inode):
        settings = super().get_folderitem_settings(request, inode)
        settings.update(
            react_component='Video',
            sample_url=inode.get_sample_url(),
        )
        return settings
