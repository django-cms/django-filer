from django.contrib import admin
from django.forms.fields import CharField, FloatField, IntegerField
from django.forms.widgets import HiddenInput, TextInput
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from entangled.forms import EntangledModelForm

from finder.admin.file import FileAdmin
from finder.contrib.image.models import ImageModel


class ImageForm(EntangledModelForm):
    name = CharField(widget=TextInput(attrs={'size': 100}))
    crop_x = FloatField(widget=HiddenInput())
    crop_y = FloatField(widget=HiddenInput())
    crop_size = FloatField(widget=HiddenInput())
    width = IntegerField(widget=HiddenInput())
    height = IntegerField(widget=HiddenInput())

    class Meta:
        model = ImageModel
        entangled_fields = {'meta_data': ['crop_x', 'crop_y', 'crop_size']}
        untangled_fields = ['name', 'width', 'height']

    class Media:
        css = {'all': ['admin/css/forms.css']}

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


@admin.register(ImageModel)
class ImageAdmin(FileAdmin):
    form = ImageForm
    readonly_fields = ['details', 'owner', 'created_at', 'last_modified_at', 'mime_type', 'sha1']

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj.mime_type in ['image/jpeg', 'image/webp']:
            readonly_fields.append('exif')
        return readonly_fields

    @admin.display(description=_("Image details"))
    def details(self, obj):
        return obj.summary

    @admin.display(description=_("EXIF-headers"))
    def exif(self, obj):
        if exif := obj.meta_data.get('exif'):
            return format_html(
                '<table>{}{}</table>',
                format_html('<tr><th>{}</th><th>{}</th></tr>', _("Tag"), _("Value")),
                format_html_join('',
                    '<tr><td>{}</td><td>{}</td></tr>',
                    ((key, value) for key, value in exif.items())
                )
            )
        return '–'

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        settings.update(
            react_component='./contrib/Image.js',
        )
        return settings
