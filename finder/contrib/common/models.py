from django.contrib.staticfiles.storage import staticfiles_storage

from finder.models.file import FileModel


class PDFFileModel(FileModel):
    accept_mime_types = ['application/pdf']
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-pdf.svg')
    editor_component = 'FileDetails'

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
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-spreadsheet.svg')
    editor_component = 'FileDetails'

    class Meta:
        proxy = True
        app_label = 'finder'
