from django.forms.fields import CharField
from django.forms.models import ModelMultipleChoiceField
from django.forms.widgets import TextInput

from entangled.forms import EntangledModelForm

from finder.models.file import FileModel
from finder.models.label import Label


class LabelsChoiceField(ModelMultipleChoiceField):
    def prepare_value(self, values):
        values = super().prepare_value(values)
        return [v for v in values if v] if hasattr(values, '__iter__') else values


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
