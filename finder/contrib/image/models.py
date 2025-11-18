from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db import models
from django.utils.functional import cached_property

from finder.models.file import AbstractFileModel


GravityChoices = {
    '': "Center",
    'n': "North",
    'ne': "Northeast",
    'e': "East",
    'se': "Southeast",
    's': "South",
    'sw': "Southwest",
    'w': "West",
    'nw': "Northwest",
}


class ImageFileModel(AbstractFileModel):
    accept_mime_types = ['image/*']
    browser_component = editor_component = 'Image'
    data_fields = AbstractFileModel.data_fields + ['width', 'height']
    thumbnail_size = 180
    fallback_thumbnail_url = staticfiles_storage.url('finder/icons/file-picture.svg')

    width = models.SmallIntegerField(default=0)
    height = models.SmallIntegerField(default=0)

    class Meta:
        app_label = 'finder'

    @cached_property
    def summary(self):
        return "{width}×{height}px ({size})".format(size=super().summary, width=self.width, height=self.height)

    def get_thumbnail_url(self, realm):
        thumbnail_filename = self.get_cropped_filename(self.thumbnail_size, self.thumbnail_size)
        thumbnail_path = f'{self.id}/{thumbnail_filename}'
        if not realm.sample_storage.exists(thumbnail_path):
            try:
                self.crop(realm, thumbnail_path, self.thumbnail_size, self.thumbnail_size)
            except Exception:
                # thumbnail image could not be created
                return self.fallback_thumbnail_url
        return realm.sample_storage.url(thumbnail_path)

    def get_cropped_filename(self, width, height):
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
        gravity = gravity if gravity in GravityChoices else ''
        return cropped_path_template.format(
            stem=file_name.stem,
            width=round(width),
            height=round(height),
            crop_x=crop_x,
            crop_y=crop_y,
            crop_size=crop_size,
            gravity=gravity,
            suffix=file_name.suffix,
        )

    def compute_crop_box(self, orig_width, orig_height, out_width, out_height):
        aspect_ratio = out_width / out_height
        assert out_width <= orig_width and out_height <= orig_height, (
            "The requested thumbnail size ({2}x{3}) is larger than the original image "
            "({0}x{1})".format(orig_width, orig_height, out_width, out_height)
        )
        orig_aspect_ratio = orig_width / orig_height
        crop_x, crop_y, crop_size, gravity = (
            self.meta_data.get('crop_x'),
            self.meta_data.get('crop_y'),
            self.meta_data.get('crop_size'),
            self.meta_data.get('gravity'),
        )
        if crop_x is None or crop_y is None or crop_size is None:
            # crop in the center of the image
            if orig_width > orig_height:
                crop_x = (orig_width - orig_height) / 2
                crop_y = 0
                crop_resize = crop_size = orig_height
            else:
                crop_x = 0
                crop_y = (orig_height - orig_width) / 2
                crop_resize = crop_size = orig_width
        elif aspect_ratio > 1:
            # optionally enlarge the crop size to the image height to prevent blurry images
            if out_height > crop_size:
                crop_resize = min(orig_height, out_height)
            else:
                crop_resize = crop_size
        else:
            # optionally enlarge the crop size to the image width to prevent blurry images
            if out_width > crop_size:
                crop_resize = min(orig_width, out_width)
            else:
                crop_resize = crop_size

        # compute the cropped area in image coordinates
        if aspect_ratio > 1:
            if aspect_ratio > orig_aspect_ratio:
                crop_width = max(min(crop_size * aspect_ratio, orig_width), out_width)
                crop_height = max(crop_width / aspect_ratio, out_height)
            else:
                crop_width = max(min(crop_size, orig_height) * aspect_ratio, out_width)
                crop_height = max(crop_width / aspect_ratio, out_height)
        else:
            if aspect_ratio < orig_aspect_ratio:
                crop_height = max(min(crop_size / aspect_ratio, orig_height), out_height)
                crop_width = max(crop_height * aspect_ratio, out_width)
            else:
                crop_height = max(min(crop_size, orig_width) / aspect_ratio, out_height)
                crop_width = max(crop_height * aspect_ratio, out_width)

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

        # ensure crop box is within image boundaries
        min_x = crop_x
        if min_x + crop_width > orig_width:
            min_x = max(orig_width - crop_width, 0)
            max_x = orig_width
        else:
            max_x = min_x + crop_width
        min_y = crop_y
        if min_y + crop_height > orig_height:
            min_y = max(orig_height - crop_height, 0)
            max_y = orig_height
        else:
            max_y = min_y + crop_height

        return min_x, min_y, max_x, max_y

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
