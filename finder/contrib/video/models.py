from pathlib import Path

from django.core.files.temp import NamedTemporaryFile
from django.contrib.staticfiles.storage import staticfiles_storage

import ffmpeg

from filer import settings as filer_settings
from finder.models.file import FileModel

SAMPLE_DURATION = 5


class VideoFileModel(FileModel):
    accept_mime_types = ['video/mp4']
    editor_component = folderitem_component = 'Video'
    thumbnail_size = 180
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-video.svg')
    filer_public_thumbnails = Path(
        filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    )

    class Meta:
        proxy = True
        app_label = 'finder'

    def get_sample_url(self, realm):
        sample_start = self.meta_data.get('sample_start')
        if sample_start is None:
            return
        sample_duration = self.meta_data.get('sample_duration', SAMPLE_DURATION)
        sample_path = f'{self.id}/{self.get_sample_path(sample_start)}'
        if not realm.sample_storage.exists(sample_path):
            suffix = Path(sample_path).suffix
            try:
                with NamedTemporaryFile(suffix=suffix) as tempfile:
                    in_stream = ffmpeg.input('pipe:0')
                    video_stream = (
                        in_stream.video
                        .filter('crop', 'min(iw,ih)', 'min(iw,ih)')
                        .filter('scale', self.thumbnail_size, -1)
                    )
                    process = (
                        ffmpeg.concat(video_stream, in_stream.audio, v=1, a=1)
                        .output(
                            tempfile.name,
                            ss=sample_start,
                            t=sample_duration,
                        )
                        .run_async(pipe_stdin=True, overwrite_output=True, quiet=True)
                    )
                    with realm.original_storage.open(self.file_path) as handle:
                        for chunk in handle.chunks():
                            try:
                                process.stdin.write(chunk)
                            except BrokenPipeError:
                                break  # sample frame found
                        process.stdin.close()
                    process.wait()
                    tempfile.flush()
                    realm.sample_storage.save(sample_path, tempfile)
            except Exception:
                return
        return realm.sample_storage.url(sample_path)

    def get_thumbnail_url(self, realm):
        sample_start = self.meta_data.get('sample_start')
        if sample_start is None:
            return self.fallback_thumbnail_url
        suffix = '.jpg'
        poster_path = f'{self.id}/{self.get_sample_path(sample_start, suffix=suffix)}'
        if not realm.sample_storage.exists(poster_path):
            try:
                with NamedTemporaryFile(suffix=suffix) as tempfile:
                    process = (
                        ffmpeg.input('pipe:0').video
                        .filter('crop', 'min(iw,ih)', 'min(iw,ih)')
                        .filter('scale', self.thumbnail_size, -1)
                        .output(tempfile.name, ss=sample_start, vframes=1)
                        .run_async(pipe_stdin=True, overwrite_output=True, quiet=True)
                    )
                    with realm.original_storage.open(self.file_path) as handle:
                        for chunk in handle.chunks():
                            try:
                                process.stdin.write(chunk)
                            except BrokenPipeError:
                                break  # sample frame found
                        process.stdin.close()
                    process.wait()
                    tempfile.flush()
                    realm.sample_storage.save(poster_path, tempfile)
            except Exception:
                return self.fallback_thumbnail_url
        return realm.sample_storage.url(poster_path)

    def get_sample_path(self, sample_start, suffix=None):
        thumbnail_path = Path(self.file_name)
        sample_start = int(sample_start * 100)
        poster_path_template = '{stem}__{sample_start}{suffix}'
        suffix = suffix or thumbnail_path.suffix
        return poster_path_template.format(
            stem=thumbnail_path.stem,
            sample_start=sample_start,
            suffix=suffix,
        )
