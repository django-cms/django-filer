from django.contrib.staticfiles.storage import staticfiles_storage

from finder.models.file import FileModel


class PDFFileModel(FileModel):
    accept_mime_types = ['application/pdf']
    editor_component = 'Common'
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-pdf.svg')

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
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-spreadsheet.svg')

    class Meta:
        proxy = True
        app_label = 'finder'


class TextFileModel(FileModel):
    accept_mime_types = [
        'text/plain',
        'text/markdown',
        'text/x-rst',
        'text/rtf',
    ]
    editor_component = 'Common'
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-text.svg')

    class Meta:
        proxy = True
        app_label = 'finder'


class CodeFileModel(FileModel):
    accept_mime_types = [
        'text/css',
        'text/html',
        'text/xml',
        'text/javascript',
        'text/x-python',
        'text/x-python-script',
        'text/x-java-source',
        'text/x-c',
        'text/x-c++',
        'text/x-csrc',
        'text/x-chdr',
        'text/x-csharp',
        'text/x-shellscript',
        'text/x-sh',
        'text/x-perl',
        'text/x-ruby',
        'text/x-php',
        'text/x-go',
        'text/x-rust',
        'text/x-scala',
        'text/x-swift',
        'text/x-kotlin',
        'text/x-sql',
        'text/x-yaml',
        'text/x-toml',
        'text/x-ini',
        'text/x-diff',
        'text/x-log',
        'text/x-cmake',
        'text/x-makefile',
        'text/x-dockerfile',
        'application/json',
        'application/xml',
        'application/javascript',
        'application/x-httpd-php',
        'application/x-sh',
        'application/x-shellscript',
        'application/xhtml+xml',
        'application/typescript',
    ]
    editor_component = 'Common'
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-code.svg')

    class Meta:
        proxy = True
        app_label = 'finder'


class WordFileModel(FileModel):
    accept_mime_types = [
        'application/rtf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.oasis.opendocument.text',
        'application/epub+zip',
        'application/epub+zip',
    ]
    editor_component = 'Common'
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-word.svg')

    class Meta:
        proxy = True
        app_label = 'finder'
