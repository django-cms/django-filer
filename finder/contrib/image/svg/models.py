from logging import getLogger
from pathlib import Path

from django.core.files.temp import NamedTemporaryFile
from django.utils.translation import gettext_lazy as _

from finder.contrib.image.models import ImageFileModel
from finder.exceptions import FileValidationError
from finder.utils import svg


logger = getLogger(__name__)


class SVGImageModel(ImageFileModel):
    """
    Model for vector images, scaled and cropped by rewriting the document
    rather than by rendering it. See :mod:`finder.utils.svg`.
    """
    accept_mime_types = ['image/svg+xml']

    class Meta:
        proxy = True
        app_label = 'finder'
        verbose_name = _("SVG Image")
        verbose_name_plural = _("SVG Images")

    def store_and_save(self, ambit, **kwargs):
        try:
            with ambit.original_storage.open(self.file_path, 'rb') as handle:
                width, height = svg.get_dimensions(handle)
        except Exception as exc:
            # A document stating its size in relative units only cannot be
            # measured without rendering it. It keeps its unset dimensions and
            # is shown with a generic icon.
            logger.warning(f"Reading the dimensions of SVG file {self.pk} failed: {exc}")
        else:
            self.width, self.height = round(width), round(height)
            if 'update_fields' in kwargs:
                kwargs['update_fields'].extend(['width', 'height'])
        super().store_and_save(ambit, **kwargs)

    def crop(self, ambit, cropped_image_path, width, height):
        with ambit.original_storage.open(self.file_path, 'rb') as handle:
            try:
                image = svg.load(handle)
            except ValueError as exc:
                raise FileValidationError(
                    _('File "{path}": SVG format not recognized ({reason})')
                    .format(path=self.pretty_path, reason=exc)
                )
        crop_box = self.compute_crop_box(image.width, image.height, width, height)
        image = image.crop(crop_box)
        image.thumbnail((width, height))
        with NamedTemporaryFile(suffix=Path(self.file_path).suffix) as tempfile:
            image.save(tempfile, format='SVG')
            ambit.sample_storage.save(cropped_image_path, tempfile)
