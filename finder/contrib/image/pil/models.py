from PIL import ExifTags, Image

from django.core.files.storage import default_storage
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from finder.contrib.image.models import ImageFileModel


class PILImageModel(ImageFileModel):
    """
    Model for image files which can be transformed by the PIL package.
    """
    accept_mime_types = ['image/jpeg', 'image/webp', 'image/png', 'image/gif']
    exif_values = set(ExifTags.Base.__members__.values())  # TODO: some EXIF values can be removed
    MAX_STORED_IMAGE_WIDTH = 3840

    class Meta:
        app_label = 'finder'
        proxy = True
        verbose_name = _('Web Image')
        verbose_name_plural = _('Web Images')

    def save(self, **kwargs):
        try:
            image = Image.open(default_storage.open(self.file_path))
            image = self.orientate_top(image)
            if self.MAX_STORED_IMAGE_WIDTH and image.width > self.MAX_STORED_IMAGE_WIDTH:
                # limit the width of the stored image to prevent excessive disk usage
                height = round(self.MAX_STORED_IMAGE_WIDTH * image.height / image.width)
                image = image.resize((self.MAX_STORED_IMAGE_WIDTH, height))
                image.save(default_storage.open(self.file_path, 'wb'), image.format)
                # recompute the file size and SHA1 hash
                self.file_size = default_storage.size(self.file_path)
                self.sha1 = self.digest_sha1()
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
        thumbnail_path = self.get_cropped_path(self.thumbnail_size, self.thumbnail_size)
        if not default_storage.exists(thumbnail_path):
            try:
                self.crop(thumbnail_path, self.thumbnail_size, self.thumbnail_size)
            except Exception:
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

    def crop(self, thumbnail_path, width, height):
        aspect_ratio = width / height
        image = Image.open(default_storage.open(self.file_path))
        assert width <= image.width and height <= image.height, \
            "The requested thumbnail size ({width}x{height}) is larger than the original image " \
            "({0}x{1})".format(*image.size, width=width, height=height)
        orig_aspect_ratio = image.width / image.height
        crop_x, crop_y, crop_size, gravity = (
            self.meta_data.get('crop_x'),
            self.meta_data.get('crop_y'),
            self.meta_data.get('crop_size'),
            self.meta_data.get('gravity'),
        )
        if crop_x is None or crop_y is None or crop_size is None:
            # crop in the center of the image
            if image.width > image.height:
                crop_x = (image.width - image.height) / 2
                crop_y = 0
                crop_resize = crop_size = image.height
            else:
                crop_x = 0
                crop_y = (image.height - image.width) / 2
                crop_resize = crop_size = image.width
        elif aspect_ratio > 1:
            # optionally enlarge the crop size to the image height to prevent blurry images
            if height > crop_size:
                crop_resize = min(image.height, height)
            else:
                crop_resize = crop_size
        else:
            # optionally enlarge the crop size to the image width to prevent blurry images
            if width > crop_size:
                crop_resize = min(image.width, width)
            else:
                crop_resize = crop_size

        # compute the cropped area in image coordinates
        if aspect_ratio > 1:
            if aspect_ratio > orig_aspect_ratio:
                crop_width = max(min(crop_size * aspect_ratio, image.width), width)
                crop_height = max(crop_width / aspect_ratio, height)
            else:
                crop_width = max(min(crop_size, image.height) * aspect_ratio, width)
                crop_height = max(crop_width / aspect_ratio, height)
        else:
            if aspect_ratio < orig_aspect_ratio:
                crop_height = max(min(crop_size / aspect_ratio, image.height), height)
                crop_width = max(crop_height * aspect_ratio, width)
            else:
                crop_height = max(min(crop_size, image.width) / aspect_ratio, height)
                crop_width = max(crop_height * aspect_ratio, width)

        # extend the horizontal crop size to prevent blurry images
        if gravity in ('e', 'ne', 'se'):
            crop_x = max(crop_x + max(crop_resize - crop_width, 0), 0)
        elif gravity in ('w', 'nw', 'sw'):
            crop_x = max(crop_x - max(min(crop_width - crop_size, crop_width), 0), 0)
        else:  # centered crop
            crop_x = max(crop_x - (crop_width - crop_size) / 2, 0)

        # extend the vertical crop size to prevent blurry images
        if gravity in ('s', 'se', 'sw'):
            crop_y = max(crop_y + max(crop_resize - crop_height, 0), 0)
        elif gravity in ('n', 'ne', 'nw'):
            crop_y = max(crop_y - max(min(crop_height - crop_size, crop_height), 0), 0)
        else:  # centered crop
            crop_y = max(crop_y - (crop_height - crop_size) / 2, 0)

        min_x = crop_x
        if min_x + crop_width > image.width:
            min_x = max(image.width - crop_width, 0)
            max_x = image.width
        else:
            max_x = min_x + crop_width
        min_y = crop_y
        if min_y + crop_height > image.height:
            min_y = max(image.height - crop_height, 0)
            max_y = image.height
        else:
            max_y = min_y + crop_height

        image = image.crop((min_x, min_y, max_x, max_y))
        image.thumbnail((width, height))
        (default_storage.base_location / thumbnail_path.parent).mkdir(parents=True, exist_ok=True)
        image.save(default_storage.open(thumbnail_path, 'wb'), image.format)
        return image
