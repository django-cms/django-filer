from django.contrib import admin
from django.forms.fields import CharField, FloatField, IntegerField
from django.forms.widgets import HiddenInput, TextInput

from finder.admin.file import FileAdmin, FileModelForm
from finder.contrib.image.models import ImageModel


class ImageForm(FileModelForm):
    crop_x = FloatField(
        widget=HiddenInput(),
        required=False,
    )
    crop_y = FloatField(
        widget=HiddenInput(),
        required=False,
    )
    crop_size = FloatField(
        widget=HiddenInput(),
        required=False,
    )
    width = IntegerField(widget=HiddenInput())
    height = IntegerField(widget=HiddenInput())
    alt_text = CharField(
        widget=TextInput(attrs={'size': 100}),
        required=False,
    )

    class Meta:
        model = ImageModel
        entangled_fields = {'meta_data': ['crop_x', 'crop_y', 'crop_size', 'alt_text']}
        untangled_fields = ['name', 'labels', 'width', 'height']

    class Media:
        css = {'all': ['admin/css/forms.css']}


@admin.register(ImageModel)
class ImageAdmin(FileAdmin):
    form = ImageForm

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        settings.update(
            original_url=settings['download_url'],
            replacing_mime_type=settings['file_mime_type'],
        )
        return settings
