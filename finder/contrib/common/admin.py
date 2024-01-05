from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.common.models import PDFFileModel, SpreadsheetModel


admin.site.register(PDFFileModel, FileAdmin)
admin.site.register(SpreadsheetModel, FileAdmin)
