from django.contrib import admin
from django.forms.models import ModelForm
from django.forms.widgets import TextInput

from finder.models.label import Label


class LabelForm(ModelForm):
    class Meta:
        model = Label
        fields = '__all__'
        widgets = {
            'color': TextInput(attrs={'type': 'color'}),
        }


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    form = LabelForm
    list_display = ['name']

