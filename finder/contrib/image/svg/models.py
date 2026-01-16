from pathlib import Path

from django.core.files.temp import NamedTemporaryFile
from django.utils.translation import gettext_lazy as _

from finder.contrib.image.models import ImageFileModel
from finder.exceptions import FileValidationError

from reportlab.graphics import renderSVG
from svglib.svglib import svg2rlg


class SVGImageModel(ImageFileModel):
    accept_mime_types = ['image/svg+xml']

    class Meta:
        proxy = True
        app_label = 'finder'
        verbose_name = _("SVG Image")
        verbose_name_plural = _("SVG Images")

    def store_and_save(self, ambit, **kwargs):
        try:
            with ambit.original_storage.open(self.file_path, 'rb') as handle:
                drawing = svg2rlg(handle)
            self.width = drawing.width
            self.height = drawing.height
        except Exception:
            pass
        else:
            if 'update_fields' in kwargs:
                kwargs['update_fields'].extend(['width', 'height'])
        super().store_and_save(ambit, **kwargs)

    def crop(self, ambit, thumbnail_path, width, height):
        with ambit.original_storage.open(self.file_path, 'rb') as handle:
            drawing = svg2rlg(handle)
        if not drawing:
            raise FileValidationError(
                _('File "{path}": SVG format not recognized')
                .format(path=self.pretty_path)
            )
        crop_box = self.compute_crop_box(drawing.width, drawing.height, width, height)
        crop_w = crop_box[2] - crop_box[0]
        crop_h = crop_box[3] - crop_box[1]
        min_y = crop_box[3] - drawing.height
        canvas = renderSVG.SVGCanvas(size=(crop_w, crop_h), useClip=True)
        canvas.svg.setAttribute('viewBox', '{0} {1} {2} {3}'.format(crop_box[0], min_y, crop_w, crop_h))
        canvas.svg.setAttribute('width', '{}'.format(crop_w))
        canvas.svg.setAttribute('height', '{}'.format(crop_h))
        renderSVG.draw(drawing, canvas)
        xml = canvas.svg.toxml(encoding="UTF-8")  # Removes non-graphic nodes -> sanitation
        with NamedTemporaryFile(suffix=Path(self.file_path).suffix) as tempfile:
            tempfile.write(xml)  # write to binary file with utf-8 encoding
            ambit.sample_storage.save(thumbnail_path, tempfile)
