from django.contrib import admin
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from finder.contrib.image.admin import ImageAdmin
from finder.contrib.image.pil.models import PILImageModel


@admin.register(PILImageModel)
class PILImageAdmin(ImageAdmin):
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj.mime_type in ['image/jpeg', 'image/webp']:
            readonly_fields.append('exif')
        return readonly_fields

    @admin.display(description=_("EXIF-headers"))
    def exif(self, obj):
        if exif := obj.meta_data.get('exif'):
            return format_html(
                '<table><tr><th>{0}</th><th>{1}</th></tr>{2}</table>',
                _("Tag"),
                _("Value"),
                format_html_join('',
                    '<tr><td>{}</td><td>{}</td></tr>',
                    ((key, value) for key, value in exif.items())
                )
            )
        return '–'
