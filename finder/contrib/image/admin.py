from django.contrib import admin
from django.forms.fields import CharField, FloatField, IntegerField
from django.forms.widgets import HiddenInput, TextInput

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
    readonly_fields = ['owner', 'created_at', 'last_modified_at', 'summary', 'mime_type', 'sha1']

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        settings.update(
            react_component='./contrib/Image.js',
        )
        return settings
