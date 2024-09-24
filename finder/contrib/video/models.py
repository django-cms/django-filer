from pathlib import Path

from django.core.files.storage import default_storage
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.functional import classproperty

import ffmpeg

from filer import settings as filer_settings
from finder.models.file import FileModel

SAMPLE_DURATION = 5


class VideoFileModel(FileModel):
    accept_mime_types = ['video/mp4']
    thumbnail_size = 180
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-video.svg')
    filer_public_thumbnails = Path(
        filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    )

    class Meta:
        proxy = True
        app_label = 'finder'

    @classproperty
    def react_folder_extension(cls):
        return {'component': 'Video'}

    @classproperty
    def react_editor_extension(cls):
        return {'component': 'Video'}

    def get_sample_url(self):
        sample_start = self.meta_data.get('sample_start')
        if sample_start is None:
            return
        sample_path = self.get_sample_path(sample_start)
        if not default_storage.exists(sample_path):
            (default_storage.base_location / sample_path.parent).mkdir(parents=True, exist_ok=True)
            stream = ffmpeg.input(default_storage.path(self.file_path), ss=sample_start)
            video_stream = ffmpeg.trim(stream.video, duration=SAMPLE_DURATION)
            video_stream = ffmpeg.filter(video_stream, 'crop', 'min(iw,ih)', 'min(iw,ih)')
            video_stream = ffmpeg.filter(video_stream, 'scale', self.thumbnail_size, -1)
            audio_stream = ffmpeg.filter(stream.audio, 'atrim', duration=SAMPLE_DURATION)
            stream = ffmpeg.concat(video_stream, audio_stream, v=1, a=1)
            stream = ffmpeg.output(stream, default_storage.path(sample_path))
            try:
                ffmpeg.run(stream)
            except ffmpeg.Error as exp:
                return self.fallback_thumbnail_url
        return default_storage.url(sample_path)

    def get_thumbnail_url(self):
        sample_start = self.meta_data.get('sample_start')
        if sample_start is None:
            return self.fallback_thumbnail_url
        poster_path = self.get_sample_path(sample_start, suffix='.jpg')
        if not default_storage.exists(poster_path):
            (default_storage.base_location / poster_path.parent).mkdir(parents=True, exist_ok=True)
            stream = ffmpeg.input(default_storage.path(self.file_path), ss=sample_start)
            video_stream = ffmpeg.filter(stream.video, 'crop', 'min(iw,ih)', 'min(iw,ih)')
            video_stream = ffmpeg.filter(video_stream, 'scale', self.thumbnail_size, -1)
            stream = ffmpeg.output(video_stream, default_storage.path(poster_path), vframes=1)
            try:
                ffmpeg.run(stream)
            except ffmpeg.Error as exp:
                return self.fallback_thumbnail_url
        return default_storage.url(poster_path)

    def get_sample_path(self, sample_start, suffix=None):
        id = str(self.id)
        thumbnail_folder = self.filer_public_thumbnails / f'{id[0:2]}/{id[2:4]}/{id}'
        thumbnail_path = Path(self.file_name)
        sample_start = int(sample_start * 100)
        poster_path_template = '{stem}__{sample_start}{suffix}'
        suffix = suffix or thumbnail_path.suffix
        return thumbnail_folder / poster_path_template.format(
            stem=thumbnail_path.stem,
            sample_start=sample_start,
            suffix=suffix,
        )
