import uuid

from django.forms.fields import UUIDField

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
