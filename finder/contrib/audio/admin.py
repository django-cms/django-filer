from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.audio.forms import AudioFileForm
from finder.contrib.audio.models import AudioFileModel


@admin.register(AudioFileModel)
class AudioAdmin(FileAdmin):
    form = AudioFileForm

    def get_editor_settings(self, request, inode):
        return {
            **super().get_editor_settings(request, inode),
            'replace_file': True,
            'download_file': True,
        }
