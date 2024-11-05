from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.audio.forms import AudioFileForm
from finder.contrib.audio.models import AudioFileModel


@admin.register(AudioFileModel)
class AudioAdmin(FileAdmin):
    form = AudioFileForm

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(
            replace_file= True,
            download_file=True,
        )
        return settings

    def get_folderitem_settings(self, request, inode):
        raise NotImplementedError()
        settings = super().get_folderitem_settings(request, inode)
        settings.update(
            react_component=inode.browser_component,
            sample_url=inode.get_sample_url(),
        )
        return settings
