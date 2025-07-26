from django.forms.fields import UUIDField
from django.forms.models import ModelMultipleChoiceField

from finder.forms.widgets import FinderFileSelect


class FinderFileField(UUIDField):
    widget = FinderFileSelect
    mime_types = None
    realm = 'admin'

    def __init__(self, mime_types=None, *args, **kwargs):
        if isinstance(mime_types, (list, tuple)):
            self.mime_types = mime_types
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        widget.mime_types = self.mime_types
        return super().widget_attrs(widget)


class LabelsChoiceField(ModelMultipleChoiceField):
    def prepare_value(self, values):
        values = super().prepare_value(values)
        return [v for v in values if v] if hasattr(values, '__iter__') else values
