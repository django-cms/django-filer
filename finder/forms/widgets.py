import json
import uuid

from django.core.serializers.json import DjangoJSONEncoder
from django.forms.widgets import TextInput
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html

from finder.models.file import AbstractFileModel, FileModel


class FinderFileSelect(TextInput):
    template_name = 'finder/widgets/finder_file_select.html'
    mime_types = None
    realm = 'admin'

    class Media:
        css = {'all': ['finder/css/finder-select.css']}
        js = [format_html(
            '<script type="module" src="{}"></script>',
            static('finder/js/finder-select.js')
        )]

    def get_context(self, name, value, attrs):
        attrs = attrs or {}
        css_classes = attrs.get('class', '').split()
        css_classes.append('finder-file-field')
        attrs['class'] = ' '.join(css_classes)
        if isinstance(value, str):
            # file reference has not been stored using a `finder.models.fields.FinderFileField`
            try:
                value = FileModel.objects.get_inode(id=uuid.UUID(value), is_folder=False)
            except (ValueError, FileModel.DoesNotExist):
                pass
        if isinstance(value, AbstractFileModel):
            attrs['data-selected_file'] = json.dumps(value.as_dict, cls=DjangoJSONEncoder)
        context = super().get_context(name, value, attrs)
        context.update(
            base_url=reverse('finder-api:base-url'),
            realm='admin',
            style_url=static('finder/css/finder-browser.css'),
        )
        if isinstance(self.mime_types, (list, tuple)) and self.mime_types:
            context['mime_types'] = ','.join(self.mime_types)
        return context

    def format_value(self, value):
        if value == "" or value is None:
            return None
        if isinstance(value, AbstractFileModel):
            return value.id
        return value
