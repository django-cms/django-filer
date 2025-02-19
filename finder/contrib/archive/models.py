from django.contrib.staticfiles.storage import staticfiles_storage

from finder.models.file import FileModel


class ArchiveModel(FileModel):
    accept_mime_types = ['application/zip', 'application/x-tar', 'application/x-gzip']
    editor_component = 'Archive'
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-zip.svg')

    class Meta:
        proxy = True
        app_label = 'finder'
