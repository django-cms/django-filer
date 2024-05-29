from pathlib import Path

from django.core.files.storage import default_storage
from django.contrib.staticfiles.storage import staticfiles_storage

from filer import settings as filer_settings
from finder.models.file import FileModel

from pydub import AudioSegment


SAMPLE_DURATION = 5


class AudioFileModel(FileModel):
    accept_mime_types = ['audio/mpeg', 'audio/ogg', 'audio/wav', 'audio/x-wav', 'audio/opus']
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-audio.svg')
    filer_public_thumbnails = Path(
        filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    )
    folder_component = editor_component = 'Audio'

    class Meta:
        proxy = True
        app_label = 'finder'

    def get_sample_url(self):
        sample_start = self.meta_data.get('sample_start', 0)
        sample_duration = self.meta_data.get('sample_duration', SAMPLE_DURATION)
        sample_path = self.get_sample_path(sample_start, sample_duration)
        if not default_storage.exists(sample_path):
            (default_storage.base_location / sample_path.parent).mkdir(parents=True, exist_ok=True)
            audio_sample = AudioSegment.from_file(
                default_storage.path(self.file_path),
                start_second=sample_start,
                duration=sample_duration,
            )
            audio_sample.export(default_storage.path(sample_path))
        return default_storage.url(sample_path)

    def get_sample_path(self, sample_start, sample_duration):
        id = str(self.id)
        thumbnail_folder = self.filer_public_thumbnails / f'{id[0:2]}/{id[2:4]}/{id}'
        thumbnail_path = Path(self.file_name)
        sample_start, sample_end = int(sample_start * 10), int(sample_duration * 10)
        sample_path_template = '{stem}__{sample_start}_{sample_end}{suffix}'
        return thumbnail_folder / sample_path_template.format(
            stem=thumbnail_path.stem,
            sample_start=sample_start,
            sample_end=sample_end,
            suffix=thumbnail_path.suffix,
        )
