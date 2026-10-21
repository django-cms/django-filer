from django.forms.fields import CharField
from django.forms.models import ModelForm
from django.forms.widgets import TextInput
from django.utils.translation import gettext_lazy as _

from finder.forms.fields import TagChoiceField
from finder.models.file import FileModel
from finder.models.filetag import LabelTag


class FileForm(ModelForm):
    name = CharField(
        widget=TextInput(attrs={'size': 100}),
    )
    label_tags = TagChoiceField(
        label=_("Label Tags"),
        queryset=LabelTag.objects.all(),
        required=False,
    )

    class Meta:
        model = FileModel
        exclude = ['meta_data']

    def get_initial_for_field(self, field, field_name: str):
        if field_name == 'label_tags':
            return self.instance.tags.all()
        return super().get_initial_for_field(field, field_name)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.tags.set(self.cleaned_data['label_tags'])
        if commit:
            instance.save()
        return instance
