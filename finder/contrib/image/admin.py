from django.contrib import admin
from django.forms.fields import CharField, FloatField, IntegerField
from django.forms.widgets import HiddenInput, TextInput

from entangled.forms import EntangledModelForm

from finder.admin.file import FileAdmin
from finder.contrib.image.models import ImageModel


class ImageForm(EntangledModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
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
        untangled_fields = ['name', 'width', 'height']

    class Media:
        css = {'all': ['admin/css/forms.css']}


@admin.register(ImageModel)
class ImageAdmin(FileAdmin):
    form = ImageForm
    exclude = None
