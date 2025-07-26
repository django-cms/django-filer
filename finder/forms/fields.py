from django.forms.fields import UUIDField
from django.forms.models import ModelMultipleChoiceField

from finder.forms.widgets import FinderFileSelect


class FinderFileField(UUIDField):
    widget = FinderFileSelect
    realm = 'admin'

    def __init__(self, *args, **kwargs):
        self.accept_mime_types = kwargs.pop('accept_mime_types', None)
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        widget.accept_mime_types = self.accept_mime_types
        return super().widget_attrs(widget)


class LabelsChoiceField(ModelMultipleChoiceField):
    def prepare_value(self, values):
        values = super().prepare_value(values)
        return [v for v in values if v] if hasattr(values, '__iter__') else values
