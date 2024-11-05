from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.image.forms import ImageFileForm
from finder.contrib.image.models import ImageFileModel


@admin.register(ImageFileModel)
class ImageAdmin(FileAdmin):
    form = ImageFileForm

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(
            replace_file= True,
            download_file=True,
            view_original=True,
        )
        return settings
