from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.common.models import PDFFileModel, SpreadsheetModel


class CommonAdmin(FileAdmin):
    """
    Admin class for common file types like PDF and spreadsheets, which do not require any special handling
    on the client side.
    """

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        settings.update(
            original_url=settings['download_url'],
            replacing_mime_type=settings['file_mime_type'],
        )
        return settings


admin.site.register(PDFFileModel, CommonAdmin)
admin.site.register(SpreadsheetModel, CommonAdmin)
