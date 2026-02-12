from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.video.forms import VideoFileForm
from finder.contrib.video.models import VideoFileModel


@admin.register(VideoFileModel)
class VideoAdmin(FileAdmin):
    form = VideoFileForm

    def get_editor_settings(self, request, inode):
        return {
            **super().get_editor_settings(request, inode),
            'replace_file': True,
            'download_file': True,
        }
