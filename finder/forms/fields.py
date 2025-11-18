from django.forms.fields import UUIDField
from django.forms.models import ModelMultipleChoiceField

from finder.forms.widgets import FinderFileSelect
from finder.models.realm import RealmModel


class FinderFileField(UUIDField):
    widget = FinderFileSelect

    def __init__(self, *args, **kwargs):
        self.accept_mime_types = kwargs.pop('accept_mime_types', None)
        self.realm = kwargs.pop('realm', None)
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        widget.accept_mime_types = self.accept_mime_types
        if isinstance(self.realm, RealmModel):
            widget.realm = self.realm
        else:
            widget.realm = RealmModel.objects.get_default(self.realm)
        return super().widget_attrs(widget)


class LabelsChoiceField(ModelMultipleChoiceField):
    def prepare_value(self, values):
        values = super().prepare_value(values)
        return [v for v in values if v] if hasattr(values, '__iter__') else values
