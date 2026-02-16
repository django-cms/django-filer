from django.forms.fields import UUIDField
from django.forms.models import ModelMultipleChoiceField

from finder.forms.widgets import FinderFileSelect, FinderFolderSelect


class FinderFileField(UUIDField):
    widget = FinderFileSelect

    def __init__(self, *args, **kwargs):
        self.accept_mime_types = kwargs.pop('accept_mime_types', None)
        self.ambit = kwargs.pop('ambit', None)
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        widget.accept_mime_types = self.accept_mime_types
        widget.ambit = self.ambit
        return super().widget_attrs(widget)


class FinderFolderField(UUIDField):
    widget = FinderFolderSelect

    def __init__(self, *args, **kwargs):
        self.ambit = kwargs.pop('ambit', None)
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        widget.ambit = self.ambit
        return super().widget_attrs(widget)


class TagChoiceField(ModelMultipleChoiceField):
    def prepare_value(self, values):
        values = super().prepare_value(values)
        return [v for v in values if v] if hasattr(values, '__iter__') else values
