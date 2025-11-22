import json
import uuid

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.widgets import TextInput
from django.urls import reverse
from django.utils.html import format_html

from finder.models.file import AbstractFileModel, FileModel
from finder.models.folder import FolderModel


class FinderInodeSelect(TextInput):
    class Media:
        css = {'all': ['finder/css/finder-select.css']}
        js = [format_html(
            '<script type="module" src="{}"></script>',
            staticfiles_storage.url('finder/js/finder-select.js')
        )]


class FinderFileSelect(FinderInodeSelect):
    template_name = 'finder/widgets/finder_file_select.html'
    accept_mime_types = None

    def get_context(self, name, value, attrs):
        attrs = attrs or {}
        css_classes = attrs.get('class', '').split()
        css_classes.append('finder-hidden-input')
        attrs['class'] = ' '.join(css_classes)
        if isinstance(value, str):
            # file reference has not been stored using a `finder.models.fields.FinderFileField`
            try:
                value = FileModel.objects.get_inode(id=uuid.UUID(value), is_folder=False)
            except (ValueError, FileModel.DoesNotExist):
                pass
        if isinstance(value, AbstractFileModel):
            attrs['data-selected_file'] = json.dumps(value.as_dict(self.realm), cls=DjangoJSONEncoder)
        context = super().get_context(name, value, attrs)
        context.update(
            base_url=reverse('finder-api:base-url'),
            realm=self.realm.slug,
            style_url=staticfiles_storage.url('finder/css/finder-browser.css'),
        )
        if isinstance(self.accept_mime_types, (list, tuple)) and self.accept_mime_types:
            context['mime_types'] = ','.join(self.accept_mime_types)
        return context

    def format_value(self, value):
        if value == '' or value is None:
            return None
        if isinstance(value, AbstractFileModel):
            return value.id
        return value


class FinderFolderSelect(FinderInodeSelect):
    template_name = 'finder/widgets/finder_folder_select.html'

    def get_context(self, name, value, attrs):
        attrs = attrs or {}
        css_classes = attrs.get('class', '').split()
        css_classes.append('finder-hidden-input')
        attrs['class'] = ' '.join(css_classes)
        if isinstance(value, str):
            # file reference has not been stored using a `finder.models.fields.FinderFileField`
            try:
                value = FolderModel.objects.get(id=uuid.UUID(value))
            except (ValueError, FolderModel.DoesNotExist):
                pass
        if isinstance(value, FolderModel):
            attrs['data-selected_folder'] = json.dumps(value.as_dict(self.realm), cls=DjangoJSONEncoder)
        context = super().get_context(name, value, attrs)
        context.update(
            base_url=reverse('finder-api:base-url'),
            realm=self.realm.slug,
            style_url=staticfiles_storage.url('finder/css/finder-browser.css'),
            folder_icon_url=staticfiles_storage.url('finder/icons/folder.svg'),
        )
        return context

    def format_value(self, value):
        if value == '' or value is None:
            return None
        if isinstance(value, FolderModel):
            return value.id
        return value
