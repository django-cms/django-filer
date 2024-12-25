from django.forms.fields import CharField
from django.forms.models import ModelForm
from django.forms.widgets import TextInput

from finder.forms.fields import LabelsChoiceField
from finder.models.file import FileModel
from finder.models.label import Label


class FileForm(ModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
    labels = LabelsChoiceField(
        queryset=Label.objects.all(),
        required=False,
    )

    class Meta:
        model = FileModel
        exclude = ['meta_data']
