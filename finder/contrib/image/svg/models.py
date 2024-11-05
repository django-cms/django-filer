from django.core.files.storage import default_storage
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

    def clean_(self):
        try:
            drawing = svg2rlg(default_storage.path(self.file_path))
            self.width = drawing.width
            self.height = drawing.height
        except Exception:
            raise FileValidationError(
                _('File "{path}": SVG format not recognized')
                .format(path=self.pretty_path)
            )

    def save(self, **kwargs):
        try:
            drawing = svg2rlg(default_storage.path(self.file_path))
            self.width = drawing.width
            self.height = drawing.height
        except Exception:
            pass
        else:
            if 'update_fields' in kwargs:
                kwargs['update_fields'].extend(['width', 'height'])
        super().save(**kwargs)

    def get_thumbnail_url(self):
        crop_x, crop_y, crop_size = (
            self.meta_data.get('crop_x'), self.meta_data.get('crop_y'), self.meta_data.get('crop_size')
        )
        thumbnail_path = self.get_thumbnail_path(crop_x, crop_y, crop_size)
        if not default_storage.exists(thumbnail_path):
            drawing = svg2rlg(default_storage.path(self.file_path))
            if not drawing:
                raise FileValidationError(
                    _('File "{path}": SVG format not recognized')
                    .format(path=self.pretty_path)
                )
            canvas = renderSVG.SVGCanvas(size=(drawing.width, drawing.height), useClip=True)
            (default_storage.base_location / thumbnail_path.parent).mkdir(parents=True, exist_ok=True)
            with default_storage.open(thumbnail_path, 'wb') as file:
                if crop_x is None or crop_y is None or crop_size is None:
                    bbox = self.centered_bounding_box(canvas)
                else:
                    bbox = crop_x, crop_y, crop_size, crop_size
                canvas.svg.setAttribute('viewBox', '{0} {1} {2} {3}'.format(*bbox))
                canvas.svg.setAttribute('width', '{2}'.format(*bbox))
                canvas.svg.setAttribute('height', '{3}'.format(*bbox))
                renderSVG.draw(drawing, canvas)
                xml = canvas.svg.toxml(encoding="UTF-8")  # Removes non-graphic nodes -> sanitation
                file.seek(0)  # Rewind file
                file.write(xml)  # write to binary file with utf-8 encoding
        return default_storage.url(thumbnail_path)

    def centered_bounding_box(self, canvas):
        bbox = [float(b) for b in canvas.svg.getAttribute('viewBox').split()]
        current_aspect_ratio = (bbox[2] - bbox[0]) / (bbox[3] - bbox[1])
        if current_aspect_ratio > 1:
            bbox[0] += (bbox[2] - bbox[3]) / 2
            bbox[2] = bbox[3]
        else:
            bbox[1] += (bbox[3] - bbox[2]) / 2
            bbox[3] = bbox[2]
        return bbox
