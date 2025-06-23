import json

from django.core.serializers.json import DjangoJSONEncoder
from django.forms.widgets import TextInput
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html

from finder.models.file import AbstractFileModel


class FinderFileSelect(TextInput):
    template_name = 'finder/widgets/finder_file_select.html'

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
        context = super().get_context(name, value, attrs)
        context.update(
            base_url=reverse('finder-api:base-url'),
            realm='admin',
            style_url=static('finder/css/finder-browser.css'),
        )
        if isinstance(value, AbstractFileModel):
            context['selected_file'] = json.dumps(value.as_dict, cls=DjangoJSONEncoder)
        return context

    def format_value(self, value):
        if value == "" or value is None:
            return None
        return value.id
