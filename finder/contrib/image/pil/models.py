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
        thumbnail_path = self.get_thumbnail_path(self.thumbnail_size, self.thumbnail_size)
        if str(self.id) == 'a118a297-0931-4ee9-95c7-925624d3b7a3' or not default_storage.exists(thumbnail_path):
            try:
                self.crop(thumbnail_path, self.thumbnail_size, self.thumbnail_size * 2.5)
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
        image = self.orientate_top(image)
        print(f"Wanted size: width={width}, height={height}, aspect_ratio={aspect_ratio} orig={image.size}")
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
            offset_x = offset_y = 0
        # elif width > height:
        #     if width > crop_size * aspect_ratio:
        #         # extend the crop size to prevent blurry images
        #         crop_x = max(crop_x - (width - crop_size) / 2, 0)
        #         crop_y = max(crop_y - (height - crop_size) / 2, 0)
        #         crop_size = width
        elif aspect_ratio > 1:
            if height > crop_size:
                crop_resize = min(image.height, height)
            else:
                crop_resize = crop_size
            offset_y = crop_resize - crop_size
            offset_x = offset_y * aspect_ratio
        else:
            if width > crop_size:
                crop_resize = min(image.width, width)
            else:
                crop_resize = crop_size
            offset_x = crop_resize - crop_size
            offset_y = offset_x / aspect_ratio

        # extend the horizontal crop size to prevent blurry images
        if gravity in ('e', 'ne', 'se'):
            if crop_resize >= crop_size:
                crop_x # += (width - crop_resize) / 2
            elif aspect_ratio > 1:
                if aspect_ratio > orig_aspect_ratio:
                    crop_x = max(crop_x - crop_resize * (aspect_ratio - 1), 0)
            else:
                crop_x = max(crop_x + crop_size - image.height * aspect_ratio, 0)
        elif gravity in ('w', 'nw', 'sw'):
            if crop_resize >= crop_size:
                crop_x = max(crop_x + crop_size - width, 0)
            elif aspect_ratio > 1:
                crop_x = max(crop_x - crop_resize * (aspect_ratio - 1), 0)
        else:  # centered crop
            if aspect_ratio < orig_aspect_ratio and crop_resize / aspect_ratio > image.height:
                crop_x = max(crop_x + (crop_size - image.height * aspect_ratio) / 2, 0)
            elif False and aspect_ratio > orig_aspect_ratio and crop_resize * aspect_ratio < image.width:
                crop_x = max(crop_x - crop_resize * (aspect_ratio - 1) / 2, 0)
            elif crop_resize > crop_size:
                crop_x = max(crop_x - offset_x / 2, 0)

        # extend the vertical crop size to prevent blurry images
        if gravity in ('n', 'ne', 'nw'):
            if crop_resize >= crop_size:
                crop_y = max(crop_y + crop_size - height, 0)
            elif aspect_ratio < 1:
                crop_y = max(crop_y + crop_size * (1 - 1 / aspect_ratio), 0)
        elif gravity in ('s', 'se', 'sw'):
            if crop_resize >= crop_size:
                crop_y # += (height - crop_resize) / 2
            elif aspect_ratio < 1:
                if aspect_ratio < orig_aspect_ratio:
                    crop_y = max(crop_y + crop_resize * (1 - 1 / aspect_ratio), 0)
                else:
                    crop_y
            else:
                crop_y = max(crop_y + (crop_size - image.width / aspect_ratio), 0)
        else:  # centered crop
            # if aspect_ratio < orig_aspect_ratio and crop_resize / aspect_ratio > image.height:
            #     crop_x = max(crop_x + (crop_size - image.height * aspect_ratio) / 2, 0)
            # elif aspect_ratio > orig_aspect_ratio and crop_resize * aspect_ratio < image.width:
            #     crop_x = max(crop_x - crop_resize * (aspect_ratio - 1) / 2, 0)
            if aspect_ratio > orig_aspect_ratio and crop_resize * aspect_ratio > image.width:
                crop_y = max(crop_y + crop_resize * (1 - 1 / aspect_ratio) / 2, 0)
            elif False and aspect_ratio < orig_aspect_ratio and crop_resize / aspect_ratio < image.height:
                crop_y = max(crop_y + (crop_size - image.width / aspect_ratio) / 2, 0)
            elif crop_resize > crop_size:
                crop_y = max(crop_y - offset_y / 2, 0)


        crop_size = crop_resize

        print(f"Crop parameters: crop_x={crop_x}, crop_y={crop_y}, crop_size={crop_size}, gravity={gravity}")

        if aspect_ratio > 1:
            if aspect_ratio > orig_aspect_ratio:
                min_width = max(min(crop_size * aspect_ratio, image.width), width)
                min_height = max(min_width / aspect_ratio, height)
            else:
                min_width = max(min(crop_size, image.height * aspect_ratio), width)
                min_height = max(min_width / aspect_ratio, height)
        else:
            if aspect_ratio < orig_aspect_ratio:
                min_height = max(min(crop_size / aspect_ratio, image.height), height)
                min_width = max(min_height * aspect_ratio, width)
                # min_height = max(image.height, height)
                # min_width = max(min_height * aspect_ratio, height)
                # min_height = max(min(crop_size, image.width / aspect_ratio), height)
                # min_width = max(min_height * aspect_ratio, width)
            else:
                min_width = max(min(crop_size, image.height * aspect_ratio), width)
                min_height = max(min_width / aspect_ratio, height)
        if False:
            min_x = max(crop_x + (crop_size - min_width) / 2, 0)
        else:
            min_x = crop_x

        if min_x + min_width > image.width:
            min_x = max(image.width - min_width, 0)
            max_x = image.width
        else:
            max_x = min_x + min_width
        if False:
            min_y = max(crop_y + (crop_size - min_height) / 2, 0)
        else:
            min_y = crop_y
        if min_y + min_height > image.height:
            min_y = max(image.height - min_height, 0)
            max_y = image.height
        else:
            max_y = min_y + min_height

        if False:
            # horizontal thumbnailing
            if orig_height / crop_size < aspect_ratio:
                # we can't fill the thumbnailed image with the cropped part
                min_width = orig_width * crop_size / orig_height
                min_x = (orig_width - min_width) / 2
            elif aspect_ratio < 1:
                min_width = max(crop_size * aspect_ratio * 3 / 2, width)
                min_x = crop_x + (crop_size - min_width) / 2
            else:
                min_width = max(crop_size, width)
                if crop_size < min_width:
                    min_x = max(crop_x - (min_width - crop_size) / 2, 0)
                else:
                    min_x = crop_x
            if crop_size < min_width:
                # thumbnail would be smaller than the crop size, avoid blurry image
                if gravity in ('e', 'ne', 'se'):
                    max_x = min(crop_x + min_width, image.width)
                    min_x = max(max_x - min_width, 0)
                elif gravity in ('w', 'nw', 'sw'):
                    min_x = max(crop_x - min_width + crop_size, 0)
            if min_x + min_width > image.width:
                min_x = max(image.width - min_width, 0)
                max_x = image.width
            else:
                max_x = min_x + min_width

            # vertical thumbnailing

            # if False and orig_width / crop_size < aspect_ratio:
            #     # we can't fill the thumbnailed image with the cropped part
            #     min_height = orig_height
            #     min_y = 0
            if aspect_ratio > 1:
                min_height = max(crop_size * aspect_ratio * 3 / 2, height)
                min_y = crop_y + (crop_size - min_height) / 2
            else:
                min_height = max(crop_size / aspect_ratio, height)
                if crop_size < min_height:
                    min_y = max(crop_y - (min_height - crop_size) / 2, 0)
                else:
                    min_y = crop_y

            # if orig_width < orig_height:
            #     min_height = max(crop_size / aspect_ratio, height)
            # else:
            #     min_height = max(min_width / aspect_ratio, height)
            # if aspect_ratio > 1:
            #     min_y = crop_y + (crop_size - min_height) / 2
            # elif crop_size < min_height:
            #     min_y = crop_y - (min_height - crop_size) / 2
            # else:
            #     min_y = crop_y

            if crop_size < min_height:
                if gravity in ('s', 'se', 'sw'):
                    max_y = min(crop_y + min_height, image.height)
                    min_y = max(max_y - min_height, 0)
                elif gravity in ('n', 'ne', 'nw'):
                    min_y = max(crop_y - min_height + crop_size, 0)
            if min_y + min_height > image.height:
                min_y = max(image.height - min_height, 0)
                max_y = image.height
            else:
                max_y = min_y + min_height

        print(f"Crop area: ({min_x}, {min_y}) to ({max_x}, {max_y}) = {max_x - min_x} x {max_y - min_y}")
        image = image.crop((min_x, min_y, max_x, max_y))
        image.thumbnail((width, height))
        (default_storage.base_location / thumbnail_path.parent).mkdir(parents=True, exist_ok=True)
        image.save(default_storage.open(thumbnail_path, 'wb'), image.format)

    def crop_centered(self, image):
        width, height = image.size
        if width > height:
            min_x = (width - height) / 2
            min_y = 0
            max_x = (width + height) / 2
            max_y = height
        else:
            min_x = 0
            min_y = (height - width) / 2
            max_x = width
            max_y = (height + width) / 2
        return image.crop((min_x, min_y, max_x, max_y))

    def crop_eccentric(self, image, crop_x, crop_y, crop_size, gravity):
        """
        with cropping, the expected resizing could be done using:
        `image = image.crop((crop_x, crop_y, crop_x + crop_size, crop_y + crop_size))`
        however, for small selections or images in low resolution this might result
        in blurry preview images. We therefore want to use at least `thumbnail_size`
        pixels from the original image
        """
        min_size = max(crop_size, self.thumbnail_size)
        off_size = min_size - crop_size

        # horizontal thumbnailing
        if gravity in ('e', 'ne', 'se'):
            max_x = min(crop_x + min_size, image.width)
            min_x = max(max_x - min_size, 0)
        elif gravity in ('w', 'nw', 'sw'):
            min_x = max(crop_x - off_size, 0)
        else:
            min_x = max(crop_x - off_size / 2, 0)
        if min_x + min_size > image.width:
            min_x = max(image.width - min_size, 0)
            max_x = image.width
        else:
            max_x = min_x + min_size

        # vertical thumbnailing
        if gravity in ('s', 'se', 'sw'):
            max_y = min(crop_y + min_size, image.height)
            min_y = max(max_y - min_size, 0)
        elif gravity in ('n', 'ne', 'nw'):
            min_y = max(crop_y - off_size, 0)
        else:
            min_y = max(crop_y - off_size / 2, 0)
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

        return image.crop((min_x, min_y, max_x, max_y))
