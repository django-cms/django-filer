from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from filer.fields.file import AdminFileWidget
from filer.models import File
from tests.helpers import create_image


class AdminFileWidgetTests(TestCase):
    def test_widget_has_change_button(self):
        original_filename = "testimage.jpg"
        file_obj = SimpleUploadedFile(
            name=original_filename,
            content=create_image().tobytes(),
            content_type="image/jpeg",
        )
        file = File.objects.create(file=file_obj, original_filename=original_filename)

        widget = AdminFileWidget(
            rel=File._meta.get_field("test_file"), admin_site=admin.site
        )

        content = widget.render("foo", file.id, {})

        self.assertIn(
            f"/admin/filer/file/{file.id}/change/?_edit_from_widget=1", content
        )
