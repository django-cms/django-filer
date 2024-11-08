from django.forms.fields import CharField
from django.forms.widgets import TextInput

from entangled.forms import EntangledModelForm

from finder.forms.fields import LabelsChoiceField
from finder.models.file import FileModel
from finder.models.label import Label


class FileForm(EntangledModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
    labels = LabelsChoiceField(
        queryset=Label.objects.all(),
        required=False,
    )

    class Meta:
        model = FileModel
        untangled_fields = ['name', 'labels']
        exclude = ['meta_data']
