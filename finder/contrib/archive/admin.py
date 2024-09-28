from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.archive.models import ArchiveModel


class ArchiveAdmin(FileAdmin):
    """
    Admin class for archived file types like ZIP, tar and tar.gz.
    """

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(
            react_component='Archive',
            download_file=True,
        )
        return settings

    def get_menu_extension_settings(self, request):
        return {'component': 'Archive'}


admin.site.register(ArchiveModel, ArchiveAdmin)
