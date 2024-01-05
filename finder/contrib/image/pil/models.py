from PIL import ExifTags, Image

from django.core.files.storage import default_storage
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from finder.contrib.image.models import ImageModel


class PILImageModel(ImageModel):
    """
    Model for image files which can be transformed by the PIL package.
    """
    accept_mime_types = ['image/jpeg', 'image/webp', 'image/png', 'image/gif']
    exif_values = set(ExifTags.Base.__members__.values())  # TODO: some values can be removed

    class Meta:
        app_label = 'finder'
        proxy = True
        verbose_name = _('Web Image')
        verbose_name_plural = _('Web Images')

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

    def get_thumbnail_url(self):
        crop_x, crop_y, crop_size = (
            self.meta_data.get('crop_x'), self.meta_data.get('crop_y'), self.meta_data.get('crop_size')
        )
        thumbnail_path = self.get_thumbnail_path(crop_x, crop_y, crop_size)
        if not default_storage.exists(thumbnail_path):
            try:
                image = Image.open(default_storage.open(self.file_path))
                image = self.orientate_top(image)
                if crop_x is None or crop_y is None or crop_size is None:
                    image = self.crop_centered(image)
                else:
                    # with cropping, the expected resizing could be done using:
                    # `image = image.crop((crop_x, crop_y, crop_x + crop_size, crop_y + crop_size))`
                    # however, for small selections or images in low resolution this might result
                    # in blurry preview images. We therefore want to use at least `thumbnail_size`
                    # pixels from the original image
                    min_size = max(crop_size, self.thumbnail_size)
                    off_size = min_size / 2 - crop_size / 2
                    min_x = max(crop_x - off_size, 0)
                    min_y = max(crop_y - off_size, 0)
                    if min_x + min_size > image.width:
                        min_x = max(image.width - min_size, 0)
                        max_x = image.width
                    else:
                        max_x = min_x + min_size
                    if min_y + min_size > image.height:
                        min_y = max(image.height - min_size, 0)
                        max_y = image.height
                    else:
                        max_y = min_y + min_size
                    # correct thumbnailing for low resolution images with an aspect ratio unequal to 1
                    if round(max_x - min_x) > round(max_y - min_y):
                        off_size = (max_x - min_x - max_y + min_y) / 2
                        min_x += off_size
                        max_x -= off_size
                    elif round(max_x - min_x) < round(max_y - min_y):
                        off_size = (max_y - min_y - max_x + min_x) / 2
                        min_y += off_size
                        max_y -= off_size
                    image = image.crop((min_x, min_y, max_x, max_y))
                image.thumbnail((self.thumbnail_size, self.thumbnail_size))
                (default_storage.base_location / thumbnail_path.parent).mkdir(parents=True, exist_ok=True)
                image.save(default_storage.open(thumbnail_path, 'wb'), image.format)
            except Exception as exception:
                # thumbnail image could not be created
                return self.fallback_thumbnail_url
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
