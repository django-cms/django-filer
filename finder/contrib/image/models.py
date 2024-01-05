from pathlib import Path

from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import models
from django.utils.functional import cached_property

from filer import settings as filer_settings

from finder.models.file import AbstractFileModel


class ImageModel(AbstractFileModel):
    accept_mime_types = ['image/*']
    data_fields = AbstractFileModel.data_fields + ['width', 'height']
    filer_public_thumbnails = Path(
        filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    )
    thumbnail_size = 180
    fallback_thumbnail_url = staticfiles_storage.url('filer/icons/file-picture.svg')
    editor_component = 'Image'

    width = models.SmallIntegerField(default=0)
    height = models.SmallIntegerField(default=0)

    class Meta:
        app_label = 'finder'

    @cached_property
    def summary(self):
        return "{width}×{height}px ({size})".format(size=super().summary, width=self.width, height=self.height)

    def get_thumbnail_path(self, crop_x=None, crop_y=None, crop_size=None):
        id = str(self.id)
        thumbnail_folder = self.filer_public_thumbnails / f'{id[0:2]}/{id[2:4]}/{id}'
        thumbnail_path = Path(self.file_name)
        if crop_x is None or crop_y is None or crop_size is None:
            thumbnail_path_template = '{stem}__{width}x{height}{suffix}'
        else:
            crop_x, crop_y, crop_size = int(crop_x), int(crop_y), int(crop_size)
            thumbnail_path_template = '{stem}__{width}x{height}__{crop_x}_{crop_y}_{crop_size}{suffix}'
        return thumbnail_folder / thumbnail_path_template.format(
            stem=thumbnail_path.stem,
            width=self.thumbnail_size,
            height=self.thumbnail_size,
            crop_x=crop_x,
            crop_y=crop_y,
            crop_size=crop_size,
            suffix=thumbnail_path.suffix,
        )
