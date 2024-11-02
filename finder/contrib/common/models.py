from django.contrib.staticfiles.storage import staticfiles_storage

from finder.models.file import FileModel


class PDFFileModel(FileModel):
    accept_mime_types = ['application/pdf']
    editor_component = 'Common'
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-pdf.svg')

    class Meta:
        proxy = True
        app_label = 'finder'


class SpreadsheetModel(FileModel):
    accept_mime_types = [
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.oasis.opendocument.spreadsheet',
    ]
    editor_component = 'Common'
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-spreadsheet.svg')

    class Meta:
        proxy = True
        app_label = 'finder'
