import uuid

from django.forms.fields import UUIDField
from django.forms.models import ModelMultipleChoiceField

from finder.forms.widgets import FinderFileSelect


class FinderFileField(UUIDField):
    widget = FinderFileSelect

    def prepare_value(self, value):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    def to_python(self, value):
        value = super().to_python(value)
        return value


class LabelsChoiceField(ModelMultipleChoiceField):
    def prepare_value(self, values):
        values = super().prepare_value(values)
        return [v for v in values if v] if hasattr(values, '__iter__') else values
