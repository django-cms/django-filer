from os import unlink
from pathlib import Path
from tempfile import mkstemp

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

    def _copy_to_local(self, ambit):
        """
        Copy the video file from storage to a local temporary file.
        This is needed because ffmpeg cannot seek in pipe input, and MP4 files
        with the moov atom at the end require seeking to be read properly.
        """
        source_suffix = Path(self.file_name).suffix
        local_file = NamedTemporaryFile(suffix=source_suffix)
        with ambit.original_storage.open(self.file_path, 'rb') as handle:
            for chunk in handle.chunks():
                local_file.write(chunk)
        local_file.flush()
        return local_file

    def get_sample_url(self, ambit):
        sample_start = self.meta_data.get('sample_start')
        if sample_start is None:
            return
        sample_duration = self.meta_data.get('sample_duration', SAMPLE_DURATION)
        sample_path = f'{self.id}/{self.get_sample_path(sample_start)}'
        if not ambit.sample_storage.exists(sample_path):
            suffix = Path(sample_path).suffix
            try:
                fd, outpath = mkstemp(suffix=suffix)
                try:
                    with self._copy_to_local(ambit) as source_file:
                        in_stream = ffmpeg.input(source_file.name, ss=sample_start)
                        video_stream = (
                            in_stream.video
                            .filter('crop', 'min(iw,ih)', 'min(iw,ih)')
                            .filter('scale', self.thumbnail_size, -1)
                        )
                        (
                            ffmpeg.concat(video_stream, in_stream.audio, v=1, a=1)
                            .output(outpath, t=sample_duration)
                            .run(overwrite_output=True, quiet=True)
                        )
                    with open(outpath, 'rb') as outfile:
                        ambit.sample_storage.save(sample_path, outfile)
                finally:
                    unlink(outpath)
            except Exception:
                return
        return ambit.sample_storage.url(sample_path)

    def get_thumbnail_url(self, ambit):
        sample_start = self.meta_data.get('sample_start')
        if sample_start is None:
            return self.fallback_thumbnail_url
        suffix = '.jpg'
        poster_path = f'{self.id}/{self.get_sample_path(sample_start, suffix=suffix)}'
        if not ambit.sample_storage.exists(poster_path):
            try:
                fd, outpath = mkstemp(suffix=suffix)
                try:
                    with self._copy_to_local(ambit) as source_file:
                        (
                            ffmpeg.input(source_file.name, ss=sample_start).video
                            .filter('crop', 'min(iw,ih)', 'min(iw,ih)')
                            .filter('scale', self.thumbnail_size, -1)
                            .output(outpath, vframes=1)
                            .run(overwrite_output=True, quiet=True)
                        )
                    with open(outpath, 'rb') as outfile:
                        ambit.sample_storage.save(poster_path, outfile)
                finally:
                    unlink(outpath)
            except Exception:
                return self.fallback_thumbnail_url
        return ambit.sample_storage.url(poster_path)

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
