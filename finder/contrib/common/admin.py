from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.common.models import CodeFileModel, PDFFileModel, SpreadsheetModel, TextFileModel, WordFileModel


class CommonAdmin(FileAdmin):
    """
    Admin class for common file types like PDF and spreadsheets, which do not require any special handling
    on the client side.
    """

    def get_editor_settings(self, request, inode):
        return {
            **super().get_editor_settings(request, inode),
            'replace_file': True,
            'download_file': True,
        }


class PDFFileAdmin(CommonAdmin):
    def get_editor_settings(self, request, inode):
        return {
            **super().get_editor_settings(request, inode),
            'view_original': True,
        }


admin.site.register(SpreadsheetModel, CommonAdmin)
admin.site.register(TextFileModel, CommonAdmin)
admin.site.register(CodeFileModel, CommonAdmin)
admin.site.register(WordFileModel, CommonAdmin)
admin.site.register(PDFFileModel, PDFFileAdmin)
