from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import models
from django.utils.functional import cached_property

from filer import settings as filer_settings

from finder.models.file import AbstractFileModel


class ImageFileModel(AbstractFileModel):
    accept_mime_types = ['image/*']
    browser_component = editor_component = 'Image'
    data_fields = AbstractFileModel.data_fields + ['width', 'height']
    filer_public_thumbnails = Path(
        filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    )
    thumbnail_size = 180
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-picture.svg')

    width = models.SmallIntegerField(default=0)
    height = models.SmallIntegerField(default=0)

    class Meta:
        app_label = 'finder'

    @cached_property
    def summary(self):
        return "{width}×{height}px ({size})".format(size=super().summary, width=self.width, height=self.height)

    def get_cropped_path(self, width, height):
        id = str(self.id)
        thumbnail_folder = self.filer_public_thumbnails / f'{id[0:2]}/{id[2:4]}/{id}'
        file_name = Path(self.file_name)
        crop_x, crop_y, crop_size, gravity = (
            self.meta_data.get('crop_x'),
            self.meta_data.get('crop_y'),
            self.meta_data.get('crop_size'),
            self.meta_data.get('gravity'),
        )
        if crop_x is None or crop_y is None or crop_size is None:
            cropped_path_template = '{stem}__{width}x{height}{suffix}'
        else:
            crop_x, crop_y, crop_size = int(crop_x), int(crop_y), int(crop_size)
            cropped_path_template = '{stem}__{width}x{height}__{crop_x}_{crop_y}_{crop_size}{gravity}{suffix}'
        return thumbnail_folder / cropped_path_template.format(
            stem=file_name.stem,
            width=round(width),
            height=round(height),
            crop_x=crop_x,
            crop_y=crop_y,
            crop_size=crop_size,
            gravity=gravity or '',
            suffix=file_name.suffix,
        )

    def get_meta_data(self):
        alt_text = self.meta_data.get('alt_text', self.name)
        data = {
            'orig_width': self.width,
            'orig_height': self.height,
            'alt_text': alt_text,
        }
        for code, language in settings.LANGUAGES:
            if code != settings.LANGUAGE_CODE:
                key = f'alt_text_{code}'
                data[key] = self.meta_data.get(key, alt_text)
        return data
