from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.common.models import PDFFileModel, SpreadsheetModel


class CommonAdmin(FileAdmin):
    """
    Admin class for common file types like PDF and spreadsheets, which do not require any special handling
    on the client side.
    """

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(
            replace_file=True,
            download_file=True,
        )
        return settings


class PDFFileAdmin(CommonAdmin):
    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(view_original=True)
        return settings


admin.site.register(SpreadsheetModel, CommonAdmin)
admin.site.register(PDFFileModel, PDFFileAdmin)
