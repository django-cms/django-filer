from django.forms.fields import CharField
from django.forms.models import ModelForm
from django.forms.widgets import TextInput

from finder.forms.fields import TagChoiceField
from finder.models.file import FileModel
from finder.models.filetag import FileTag


class FileForm(ModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
    tags = TagChoiceField(
        queryset=FileTag.objects.all(),
        required=False,
    )

    class Meta:
        model = FileModel
        exclude = ['meta_data']
