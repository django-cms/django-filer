from pathlib import Path
from PIL import ExifTags, Image

from django.core.files.storage import default_storage
from django.db import models
from django.utils.functional import cached_property
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from filer import settings as filer_settings

from finder.models.file import AbstractFileModel


class ImageModel(AbstractFileModel):
    accept_mime_types = ['image/jpeg', 'image/webp', 'image/png', 'image/gif']
    data_fields = AbstractFileModel.data_fields + ['width', 'height']
    filer_public_thumbnails = Path(
        filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    )
    exif_values = set(ExifTags.Base.__members__.values())  # TODO: some values can be removed
    thumbnail_size = (180, 180)

    width = models.SmallIntegerField(default=0)
    height = models.SmallIntegerField(default=0)

    class Meta:
        app_label = 'finder'
        verbose_name = _('Image')
        verbose_name_plural = _('Images')

    @cached_property
    def summary(self):
        return "{width}×{height}px ({size})".format(size=super().summary, width=self.width, height=self.height)

    def save(self, **kwargs):
        try:
            image = Image.open(default_storage.open(self.file_path))
            self.width = image.width
            self.height = image.height
        except Exception:
            pass
        else:
            if 'update_fields' in kwargs:
                kwargs['update_fields'].extend(['width', 'height'])
        try:
            exif = image.getexif()
            self.meta_data.setdefault('exif', {})
            for key, value in exif.items():
                if key in self.exif_values and isinstance(value, (str, int, float, datetime)):
                    self.meta_data['exif'].setdefault(ExifTags.Base(key).name, value)
        except Exception:
            pass
        else:
            if 'update_fields' in kwargs:
                kwargs['update_fields'].append('meta_data')
        super().save(**kwargs)

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
            width=self.thumbnail_size[0],
            height=self.thumbnail_size[1],
            crop_x=crop_x,
            crop_y=crop_y,
            crop_size=crop_size,
            suffix=thumbnail_path.suffix,
        )

    def get_thumbnail_url(self):
        crop_x, crop_y, crop_size = (
            self.meta_data.get('crop_x'), self.meta_data.get('crop_y'), self.meta_data.get('crop_size')
        )
        thumbnail_path = self.get_thumbnail_path(crop_x, crop_y, crop_size)
        if not default_storage.exists(thumbnail_path):
            image = Image.open(default_storage.open(self.file_path))
            image = self.orientate_top(image)
            if crop_x is None or crop_y is None or crop_size is None:
                image = self.crop_centered(image)
            else:
                image = image.crop((crop_x, crop_y, crop_x + crop_size, crop_y + crop_size))
            image.thumbnail(self.thumbnail_size)
            (default_storage.base_location / thumbnail_path.parent).mkdir(parents=True, exist_ok=True)
            image.save(default_storage.open(thumbnail_path, 'wb'), image.format)
        return default_storage.url(thumbnail_path)

    def orientate_top(self, image):
        if exif := image.getexif():
            orientation = exif.get(ExifTags.Base.Orientation, 1)
            if orientation == 2:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:
                image = image.transpose(Image.ROTATE_180)
            elif orientation == 4:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
            elif orientation == 5:
                image = image.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 6:
                image = image.transpose(Image.ROTATE_270)
            elif orientation == 7:
                image = image.transpose(Image.ROTATE_90).transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 8:
                image = image.transpose(Image.ROTATE_90)
        return image

    def crop_centered(self, image):
        width, height = image.size
        if width > height:
            left = (width - height) / 2
            top = 0
            right = (width + height) / 2
            bottom = height
        else:
            left = 0
            top = (height - width) / 2
            right = width
            bottom = (height + width) / 2
        return image.crop((left, top, right, bottom))
