import json
import pytest
import uuid

from bs4 import BeautifulSoup

from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse

from finder.contrib.archive.models import ArchiveModel
from finder.contrib.image.forms import ImageFileForm
from finder.contrib.image.pil.models import PILImageModel
from finder.contrib.image.svg.models import SVGImageModel
from finder.forms.fields import TagChoiceField
from finder.forms.file import FileForm
from finder.forms.widgets import FinderFileSelect, FinderFolderSelect
from finder.models.file import FileModel
from finder.models.filetag import FileTag
from finder.models.folder import FolderModel

from .testapp.models import SampleAppModel1, SampleAppModel3, SampleAppModel4


@pytest.fixture
def public_file(public_ambit, admin_user):
    uploaded_file = SimpleUploadedFile('public_file.bin', b'\x00' * 50, content_type='application/octet-stream')
    return FileModel.objects.create_from_upload(
        public_ambit,
        uploaded_file,
        folder=public_ambit.root_folder,
        owner=admin_user,
    )


@pytest.fixture
def public_folder(public_ambit, admin_user):
    return FolderModel.objects.create(
        parent=public_ambit.root_folder,
        name="Public Folder",
        owner=admin_user,
    )


def test_render_form_with_empty_file_select(admin_client, public_ambit):
    response = admin_client.get(reverse('testapp'))
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    element = soup.find('finder-file-select')
    assert element is not None
    assert element['base-url'] == reverse('finder-api:base-url')
    assert element['ambit'] == 'public'
    assert element['style-url'].endswith('finder/css/finder-browser.css')
    assert element.get('mime-types') is None
    input_element = element.find('input')
    assert input_element['name'] == 'file'
    assert 'finder-hidden-input' in input_element['class']
    assert input_element.get('value') is None
    assert input_element.get('data-selected_file') is None
    # the widget pulls in its own web component
    assert 'finder/js/finder-select.js' in response.text


def test_render_form_with_selected_file(admin_client, public_ambit, public_file):
    SampleAppModel1.objects.create(file=public_file.id)
    response = admin_client.get(reverse('testapp'))
    soup = BeautifulSoup(response.content, 'html.parser')
    input_element = soup.find('finder-file-select').find('input')
    assert input_element['value'] == str(public_file.id)
    selected_file = json.loads(input_element['data-selected_file'])
    assert selected_file['id'] == str(public_file.id)
    assert selected_file['name'] == 'public_file.bin'
    assert selected_file['file_size'] == 50


def test_submit_form_with_selected_file(admin_client, public_ambit, public_file):
    obj = SampleAppModel1.objects.create()
    response = admin_client.post(reverse('testapp'), {'file': str(public_file.id)})
    assert response.status_code == 302
    obj.refresh_from_db()
    assert obj.file.id == public_file.id
    assert isinstance(obj.file, FileModel)


def test_file_select_widget_accepts_mime_types(public_ambit, public_file):
    """The `accept_mime_types` of the model field are passed down to the web component."""
    form_field = SampleAppModel3._meta.get_field('file').formfield()
    widget = form_field.widget
    form_field.widget_attrs(widget)
    context = widget.get_context('file', public_file.id, {})
    assert context['mime_types'] == 'image/*'
    assert context['ambit'] == 'public'


@pytest.mark.parametrize('value', ['not-a-uuid', str(uuid.uuid4())])
def test_file_select_widget_with_unresolvable_value(db, public_ambit, value):
    """Values which are no reference to an existing file are rendered as they are."""
    widget = FinderFileSelect()
    widget.ambit = 'public'
    widget.accept_mime_types = None
    context = widget.get_context('file', value, {})
    assert context['widget']['value'] == value
    assert 'data-selected_file' not in context['widget']['attrs']


def test_file_select_widget_resolves_uuid_string(public_ambit, public_file):
    """A file reference which has not been stored through a `FinderFileField` is resolved by its UUID."""
    widget = FinderFileSelect()
    widget.ambit = 'public'
    widget.accept_mime_types = None
    context = widget.get_context('file', str(public_file.id), {'class': 'vTextField'})
    selected_file = json.loads(context['widget']['attrs']['data-selected_file'])
    assert selected_file['id'] == str(public_file.id)
    assert context['widget']['attrs']['class'] == 'vTextField finder-hidden-input'


def test_file_select_widget_format_value(public_ambit, public_file):
    widget = FinderFileSelect()
    assert widget.format_value('') is None
    assert widget.format_value(None) is None
    assert widget.format_value(public_file) == public_file.id
    assert widget.format_value(str(public_file.id)) == str(public_file.id)


def test_render_form_with_empty_folder_select(admin_client, public_ambit):
    form_field = SampleAppModel4._meta.get_field('folder').formfield()
    widget = form_field.widget
    form_field.widget_attrs(widget)
    context = widget.get_context('folder', None, {})
    assert isinstance(widget, FinderFolderSelect)
    assert context['ambit'] == 'public'
    assert context['base_url'] == reverse('finder-api:base-url')
    assert context['folder_icon_url'].endswith('finder/icons/folder.svg')
    assert 'data-selected_folder' not in context['widget']['attrs']


def test_folder_select_widget_resolves_uuid_string(public_ambit, public_folder):
    widget = FinderFolderSelect()
    widget.ambit = 'public'
    context = widget.get_context('folder', str(public_folder.id), {})
    selected_folder = json.loads(context['widget']['attrs']['data-selected_folder'])
    assert selected_folder['id'] == str(public_folder.id)
    assert selected_folder['name'] == "Public Folder"
    assert selected_folder['is_folder'] is True


@pytest.mark.parametrize('value', ['not-a-uuid', str(uuid.uuid4())])
def test_folder_select_widget_with_unresolvable_value(db, public_ambit, value):
    widget = FinderFolderSelect()
    widget.ambit = 'public'
    context = widget.get_context('folder', value, {})
    assert context['widget']['value'] == value
    assert 'data-selected_folder' not in context['widget']['attrs']


def test_folder_select_widget_format_value(public_ambit, public_folder):
    widget = FinderFolderSelect()
    assert widget.format_value('') is None
    assert widget.format_value(None) is None
    assert widget.format_value(public_folder) == public_folder.id
    assert widget.format_value(str(public_folder.id)) == str(public_folder.id)


def test_folder_select_widget_renders_web_component(public_ambit, public_folder):
    widget = FinderFolderSelect()
    widget.ambit = 'public'
    html = widget.render('folder', public_folder.id, {})
    soup = BeautifulSoup(html, 'html.parser')
    element = soup.find('finder-folder-select')
    assert element['ambit'] == 'public'
    assert element.find('input')['value'] == str(public_folder.id)


def test_tag_choice_field_prepare_value(db, ambit):
    tag = FileTag.objects.create(ambit=ambit, label="Red", color='#ff0000')
    field = TagChoiceField(queryset=FileTag.objects.all(), required=False)
    assert field.prepare_value([tag.id, None]) == [tag.id]
    assert field.prepare_value(None) is None
    assert field.prepare_value(tag.id) == tag.id


def test_get_form_class_per_model():
    """Each file model uses the form declared by the app it belongs to, or falls back to the generic one."""
    from finder.contrib.image.pil.forms import PILImageForm
    from finder.contrib.image.svg.forms import SVGImageForm

    assert FileModel.get_form_class() is FileForm
    assert PILImageModel.get_form_class() is PILImageForm
    assert SVGImageModel.get_form_class() is SVGImageForm
    assert PILImageForm is SVGImageForm is ImageFileForm
    # no app declares an `ArchiveForm`, hence the generic file form is used
    assert ArchiveModel.get_form_class() is FileForm


def test_download_url_template_tag(db, ambit, uploaded_file):
    template = Template("{% load finder_tags %}{% download_url file_id %}")
    url = template.render(Context({'file_id': uploaded_file.id}))
    assert url == ambit.original_storage.url(uploaded_file.file_path)


def test_download_url_template_tag_for_missing_file(db, ambit, missing_inode_id):
    template = Template("{% load finder_tags %}{% download_url file_id %}")
    assert template.render(Context({'file_id': missing_inode_id})) == ''
