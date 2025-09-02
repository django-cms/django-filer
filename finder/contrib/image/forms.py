from django.forms.fields import CharField, FloatField, IntegerField
from django.forms.widgets import HiddenInput, TextInput
from django.utils.translation import gettext_lazy as _

from entangled.forms import EntangledModelFormMixin

from finder.contrib.image.models import ImageFileModel
from finder.forms.file import FileForm


class ImageFileForm(EntangledModelFormMixin, FileForm):
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
    gravity = CharField(
        widget=HiddenInput(),
        required=False,
    )
    alt_text = CharField(
        label=_("Alternative Text"),
        widget=TextInput(attrs={'size': 100}),
        required=False,
    )
    credit = CharField(
        label=_("Image Credit"),
        widget=TextInput(attrs={'size': 100}),
        required=False,
    )

    class Meta:
        model = ImageFileModel
        entangled_fields = {'meta_data': ['crop_x', 'crop_y', 'crop_size', 'gravity', 'alt_text', 'credit']}
        untangled_fields = ['name', 'labels', 'width', 'height']
