from django.forms.fields import CharField, FloatField, IntegerField
from django.forms.widgets import HiddenInput, TextInput

from finder.contrib.image.models import ImageFileModel
from finder.forms.file import FileForm


class ImageFileForm(FileForm):
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
        model = ImageFileModel
        entangled_fields = {'meta_data': ['crop_x', 'crop_y', 'crop_size', 'alt_text']}
        untangled_fields = ['name', 'labels', 'width', 'height']
