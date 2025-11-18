from pathlib import Path
from PIL import ExifTags, Image

from django.core.files.temp import NamedTemporaryFile
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _

from finder.contrib.image.models import ImageFileModel
from finder.models.file import digest_sha1


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

    def store_and_save(self, realm, **kwargs):
        try:
            image = Image.open(realm.original_storage.open(self.file_path))
            image, changed = self.orientate_top(image)
            if self.MAX_STORED_IMAGE_WIDTH and image.width > self.MAX_STORED_IMAGE_WIDTH:
                # limit the width of the stored image to prevent excessive disk usage
                height = round(self.MAX_STORED_IMAGE_WIDTH * image.height / image.width)
                image = image.resize((self.MAX_STORED_IMAGE_WIDTH, height))
                changed = True
            if changed:
                with NamedTemporaryFile(suffix=Path(self.file_path).suffix) as tempfile:
                    image.save(tempfile, image.format)
                    realm.original_storage.save(self.file_path, tempfile)
                self.file_size = realm.original_storage.size(self.file_path)
                self.sha1 = digest_sha1(realm.original_storage.open(self.file_path))
            self.width = image.width
            self.height = image.height
        except Exception:
            pass
        else:
            if 'update_fields' in kwargs:
                kwargs['update_fields'].extend(['width', 'height', 'file_size', 'sha1'])
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
        super().store_and_save(realm, **kwargs)

    def orientate_top(self, image):
        changed = False
        if exif := image.getexif():
            orientation = exif.get(ExifTags.Base.Orientation, 1)
            if orientation == 2:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
                changed = True
            elif orientation == 3:
                image = image.transpose(Image.ROTATE_180)
                changed = True
            elif orientation == 4:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                changed = True
            elif orientation == 5:
                image = image.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
                changed = True
            elif orientation == 6:
                image = image.transpose(Image.ROTATE_270)
                changed = True
            elif orientation == 7:
                image = image.transpose(Image.ROTATE_90).transpose(Image.FLIP_LEFT_RIGHT)
                changed = True
            elif orientation == 8:
                image = image.transpose(Image.ROTATE_90)
                changed = True
        return image, changed

    def crop(self, realm, thumbnail_path, width, height):
        image = Image.open(realm.original_storage.open(self.file_path))
        crop_box = self.compute_crop_box(image.width, image.height, width, height)
        image = image.crop(crop_box)
        image.thumbnail((width, height))
        with NamedTemporaryFile(suffix=Path(self.file_path).suffix) as tempfile:
            image.save(tempfile, image.format)
            realm.sample_storage.save(thumbnail_path, tempfile)
