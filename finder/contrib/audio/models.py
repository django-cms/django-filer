from logging import getLogger
from os import unlink
from pathlib import Path
from tempfile import mkstemp

from django.contrib.staticfiles.storage import staticfiles_storage

from finder.models.file import FileModel
from finder.storages import copy_to_local

import ffmpeg


SAMPLE_DURATION = 5

logger = getLogger(__name__)


class AudioFileModel(FileModel):
    accept_mime_types = ['audio/mpeg', 'audio/ogg', 'audio/wav', 'audio/x-wav', 'audio/opus']
    editor_component = folderitem_component = 'Audio'
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-audio.svg')

    class Meta:
        proxy = True
        app_label = 'finder'

    def get_sample_url(self, ambit):
        if not ambit.original_storage.exists(self.file_path):
            return
        sample_start = self.meta_data.get('sample_start', 0)
        sample_duration = self.meta_data.get('sample_duration', SAMPLE_DURATION)
        sample_path = f'{self.id}/{self.get_sample_path(sample_start, sample_duration)}'
        if not ambit.sample_storage.exists(sample_path):
            suffix = Path(sample_path).suffix
            fd, outpath = mkstemp(suffix=suffix)
            try:
                with copy_to_local(ambit.original_storage, self.file_path) as source_file:
                    (
                        ffmpeg.input(source_file.name, ss=sample_start).audio
                        .filter('atrim', duration=sample_duration)
                        .output(outpath)
                        .run(overwrite_output=True, quiet=True)
                    )
                with open(outpath, 'rb') as outfile:
                    ambit.sample_storage.save(sample_path, outfile)
            except Exception as exc:
                logger.warning(f"Sample generation failed for audio file {self.pk}: {exc}")
                return
            finally:
                unlink(outpath)
        return ambit.sample_storage.url(sample_path)

    def get_sample_path(self, sample_start, sample_duration):
        sample_path = Path(self.file_name)
        sample_start, sample_end = int(sample_start * 10), int(sample_duration * 10)
        sample_path_template = '{stem}__{sample_start}_{sample_end}{suffix}'
        return sample_path_template.format(
            stem=sample_path.stem,
            sample_start=sample_start,
            sample_end=sample_end,
            suffix=sample_path.suffix,
        )
