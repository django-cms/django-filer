from pathlib import Path

from django.core.files.storage import default_storage
from django.contrib.staticfiles.storage import staticfiles_storage

from filer import settings as filer_settings
from finder.models.file import FileModel



class VideoFileModel(FileModel):
    accept_mime_types = ['video/mp4']
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-video.svg')
    filer_public_thumbnails = Path(
        filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    )
    editor_component = 'Video'

    class Meta:
        proxy = True
        app_label = 'finder'

    def get_sample_url(self):
        return self.fallback_thumbnail_url
