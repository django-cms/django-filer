from pathlib import Path

from django.core.files.temp import NamedTemporaryFile
from django.contrib.staticfiles.storage import staticfiles_storage

from finder.models.file import FileModel

import ffmpeg


SAMPLE_DURATION = 5


class AudioFileModel(FileModel):
    accept_mime_types = ['audio/mpeg', 'audio/ogg', 'audio/wav', 'audio/x-wav', 'audio/opus']
    editor_component = folderitem_component = 'Audio'
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-audio.svg')

    class Meta:
        proxy = True
        app_label = 'finder'

    def get_sample_url(self, realm):
        if not realm.original_storage.exists(self.file_path):
            return
        sample_start = self.meta_data.get('sample_start', 0)
        sample_duration = self.meta_data.get('sample_duration', SAMPLE_DURATION)
        sample_path = f'{self.id}/{self.get_sample_path(sample_start, sample_duration)}'
        if not realm.sample_storage.exists(sample_path):
            suffix = Path(sample_path).suffix
            try:
                with NamedTemporaryFile(suffix=suffix) as tempfile:
                    process = (
                        ffmpeg.input('pipe:0').audio
                        .filter('atrim', start=sample_start, duration=sample_duration)
                        .output(tempfile.name)
                        .run_async(pipe_stdin=True, overwrite_output=True, quiet=True)
                    )
                    with realm.original_storage.open(self.file_path) as handle:
                        for chunk in handle.chunks():
                            try:
                                process.stdin.write(chunk)
                            except BrokenPipeError:
                                break  # end of sample reached
                        process.stdin.close()
                    process.wait()
                    tempfile.flush()
                    realm.sample_storage.save(sample_path, tempfile)
            except Exception:
                return
        return realm.sample_storage.url(sample_path)

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
