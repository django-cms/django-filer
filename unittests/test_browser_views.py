import json
import pytest

from io import BytesIO

from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.browser.views import BrowserView
from finder.contrib.image.pil.models import PILImageModel
from finder.models.file import FileModel
from finder.models.filetag import FileTag
from finder.models.folder import FolderModel
from finder.models.permission import AccessControlEntry, Privilege


MULTIPART = MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'}


@pytest.fixture
def api_url():
    return reverse('finder-api:base-url')


@pytest.fixture
def nested_folder(sub_folder, admin_user):
    return FolderModel.objects.create(
        parent=sub_folder,
        name='Nested Folder',
        owner=admin_user,
    )


@pytest.fixture
def staff_client(client, django_user_model):
    """A logged in user without superuser privileges, hence subject to the access control lists."""
    user = django_user_model.objects.create_user('staff', password='secret', is_staff=True)
    client.force_login(user)
    client.user = user
    return client


def test_view_without_action(admin_client, api_url):
    """The base URL is registered without an action and hence rejects any request."""
    response = admin_client.get(api_url)
    assert response.status_code == 404


def test_structure_of_empty_root_folder(admin_client, ambit, api_url):
    response = admin_client.get(f'{api_url}structure/{ambit.slug}')
    assert response.status_code == 200
    payload = response.json()
    root_folder = payload['root_folder']
    assert root_folder['id'] == str(ambit.root_folder.id)
    assert root_folder['name'] is None
    assert root_folder['is_root'] is True
    assert root_folder['is_open'] is False
    assert root_folder['children'] is None
    assert payload['tags'] == []
    assert payload['last_folder'] == str(ambit.root_folder.id)
    assert payload['files'] == []
    assert payload['has_upload_permission'] is True


def test_structure_of_unknown_ambit(admin_client, ambit, api_url):
    response = admin_client.get(f'{api_url}structure/no-such-ambit')
    assert response.status_code == 404


def test_structure_with_tags(admin_client, ambit, api_url):
    tag = FileTag.objects.create(ambit=ambit, label="Red", color='#ff0000')
    response = admin_client.get(f'{api_url}structure/{ambit.slug}')
    assert response.json()['tags'] == [{'value': tag.id, 'label': "Red", 'color': '#ff0000'}]


def test_structure_opens_ancestors_of_the_requested_folder(admin_client, ambit, nested_folder, api_url):
    """Requesting the structure for a deeply nested folder opens all of its ancestors."""
    response = admin_client.get(f'{api_url}structure/{ambit.slug}?folder={nested_folder.id}')
    assert response.status_code == 200
    payload = response.json()
    assert payload['last_folder'] == str(nested_folder.id)
    root_folder = payload['root_folder']
    assert root_folder['is_open'] is True
    sub_folder_data = root_folder['children'][0]
    assert sub_folder_data['name'] == "Sub Folder"
    assert sub_folder_data['is_open'] is True
    nested_folder_data = sub_folder_data['children'][0]
    assert nested_folder_data['name'] == "Nested Folder"
    assert nested_folder_data['is_open'] is True
    assert nested_folder_data['children'] == []


def test_structure_with_closed_subfolder(admin_client, ambit, sub_folder, api_url):
    response = admin_client.get(f'{api_url}structure/{ambit.slug}')
    sub_folder_data = response.json()['root_folder']['children'][0]
    assert sub_folder_data['id'] == str(sub_folder.id)
    assert sub_folder_data['is_open'] is False
    assert sub_folder_data['children'] is None


def test_structure_falls_back_to_root_folder(admin_client, ambit, sub_folder, missing_inode_id, api_url):
    """A folder which has been removed in the meantime falls back to the root folder."""
    response = admin_client.get(f'{api_url}structure/{ambit.slug}?folder={missing_inode_id}')
    assert response.status_code == 200
    payload = response.json()
    assert payload['last_folder'] == str(ambit.root_folder.id)
    assert payload['root_folder']['children'][0]['id'] == str(sub_folder.id)


def test_structure_hides_folders_without_read_permission(staff_client, ambit, sub_folder, api_url):
    """The subfolder has no access control entry and hence is invisible for a non-superuser."""
    response = staff_client.get(f'{api_url}structure/{ambit.slug}')
    assert response.status_code == 200
    assert response.json()['root_folder']['children'] == []

    AccessControlEntry.objects.create(inode=sub_folder.id, user=staff_client.user, privilege=Privilege.READ)
    response = staff_client.get(f'{api_url}structure/{ambit.slug}')
    assert response.json()['root_folder']['children'][0]['id'] == str(sub_folder.id)


def test_fetch_folder(admin_client, ambit, nested_folder, sub_folder, api_url):
    response = admin_client.get(f'{api_url}{sub_folder.id}/fetch')
    assert response.status_code == 200
    payload = response.json()
    assert payload['id'] == str(sub_folder.id)
    assert payload['name'] == "Sub Folder"
    assert payload['is_open'] is True
    assert payload['has_subfolders'] is True
    assert [child['id'] for child in payload['children']] == [str(nested_folder.id)]
    assert admin_client.session['finder.open_folders'] == [str(sub_folder.id)]

    # fetching the same folder again keeps it open exactly once
    response = admin_client.get(f'{api_url}{sub_folder.id}/fetch')
    assert response.status_code == 200
    assert admin_client.session['finder.open_folders'] == [str(sub_folder.id)]


def test_fetch_file(admin_client, ambit, uploaded_file, api_url):
    response = admin_client.get(f'{api_url}{uploaded_file.id}/fetch')
    assert response.status_code == 200
    payload = response.json()
    assert payload['id'] == str(uploaded_file.id)
    assert payload['name'] == uploaded_file.name
    assert payload['file_size'] == uploaded_file.file_size
    assert payload['mime_type'] == uploaded_file.mime_type


def test_fetch_missing_inode(admin_client, ambit, missing_inode_id, api_url):
    response = admin_client.get(f'{api_url}{missing_inode_id}/fetch')
    assert response.status_code == 404


def test_open_and_close_folder(client, ambit, sub_folder, api_url):
    # closing a folder before the session has been initialized is a no-op
    response = client.get(f'{api_url}{sub_folder.id}/close')
    assert response.status_code == 200
    assert response.json() == {'id': str(sub_folder.id)}

    response = client.get(f'{api_url}{sub_folder.id}/open')
    assert response.json() == {'id': str(sub_folder.id)}
    assert client.session['finder.open_folders'] == [str(sub_folder.id)]

    # opening the same folder twice does not duplicate the entry
    client.get(f'{api_url}{sub_folder.id}/open')
    assert client.session['finder.open_folders'] == [str(sub_folder.id)]

    client.get(f'{api_url}{sub_folder.id}/close')
    assert client.session['finder.open_folders'] == []

    # closing a folder which is not open is a no-op
    response = client.get(f'{api_url}{sub_folder.id}/close')
    assert response.status_code == 200
    assert client.session['finder.open_folders'] == []


def test_open_folder_rejects_post(admin_client, ambit, sub_folder, api_url):
    """The endpoint is restricted to GET requests. The rejection is reported as “bad request”."""
    response = admin_client.post(f'{api_url}{sub_folder.id}/open')
    assert response.status_code == 400


def test_list_files(admin_client, ambit, uploaded_file, sub_folder, api_url):
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    assert response.status_code == 200
    payload = response.json()
    assert payload['offset'] is None
    assert payload['recursive'] is False
    assert payload['search_query'] == ''
    assert payload['has_upload_permission'] is True
    # folders are not part of the listing
    assert [entry['id'] for entry in payload['files']] == [str(uploaded_file.id)]
    entry = payload['files'][0]
    assert entry['name'] == uploaded_file.name
    assert entry['download_url'].endswith(uploaded_file.file_name)
    assert 'thumbnail_url' in entry
    assert 'preview_url' in entry
    assert 'sample_url' in entry
    assert entry['summary'] == uploaded_file.summary
    assert 'name_lower' not in entry
    assert admin_client.session['finder.last_folder'] == str(ambit.root_folder.id)


def test_list_missing_folder(admin_client, ambit, missing_inode_id, api_url):
    response = admin_client.get(f'{api_url}{missing_inode_id}/list')
    assert response.status_code == 404


def test_list_files_recursively(admin_client, ambit, admin_user, uploaded_file, sub_folder, api_url):
    nested_file = FileModel.objects.create_from_upload(
        ambit,
        SimpleUploadedFile('nested.bin', b'\x00' * 10, content_type='application/octet-stream'),
        folder=sub_folder,
        owner=admin_user,
    )
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    assert [entry['id'] for entry in response.json()['files']] == [str(uploaded_file.id)]

    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list?recursive')
    payload = response.json()
    assert payload['recursive'] is True
    assert {entry['id'] for entry in payload['files']} == {str(uploaded_file.id), str(nested_file.id)}


def test_list_files_filtered_by_mime_type(admin_client, ambit, uploaded_file, uploaded_image, api_url):
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list?mimetypes=image/*')
    assert [entry['id'] for entry in response.json()['files']] == [str(uploaded_image.id)]

    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list?mimetypes=application/octet-stream')
    assert [entry['id'] for entry in response.json()['files']] == [str(uploaded_file.id)]


def test_list_files_filtered_by_tag(admin_client, ambit, uploaded_file, uploaded_image, api_url):
    red_tag = FileTag.objects.create(ambit=ambit, label="Red", color='#ff0000')
    blue_tag = FileTag.objects.create(ambit=ambit, label="Blue", color='#0000ff')
    uploaded_file.tags.add(red_tag)

    admin_client.cookies['django-finder-filter'] = str(red_tag.id)
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    files = response.json()['files']
    assert [entry['id'] for entry in files] == [str(uploaded_file.id)]
    assert files[0]['tags'] == [{'id': red_tag.id, 'label': "Red", 'color': '#ff0000'}]

    admin_client.cookies['django-finder-filter'] = str(blue_tag.id)
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    assert response.json()['files'] == []

    # unparsable and unknown tag filters are ignored
    for invalid_filter in ['not-a-number', str(blue_tag.id + 100)]:
        admin_client.cookies['django-finder-filter'] = invalid_filter
        response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
        assert len(response.json()['files']) == 2


def test_list_files_sorted(admin_client, ambit, admin_user, api_url):
    for name in ['charlie.bin', 'alpha.bin', 'bravo.bin']:
        FileModel.objects.create_from_upload(
            ambit,
            SimpleUploadedFile(name, b'\x00' * 10, content_type='application/octet-stream'),
            folder=ambit.root_folder,
            owner=admin_user,
        )

    admin_client.cookies['django-finder-sorting'] = 'name_asc'
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    assert [entry['name'] for entry in response.json()['files']] == ['alpha.bin', 'bravo.bin', 'charlie.bin']

    admin_client.cookies['django-finder-sorting'] = 'name_desc'
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    assert [entry['name'] for entry in response.json()['files']] == ['charlie.bin', 'bravo.bin', 'alpha.bin']


def test_list_files_paginated(admin_client, ambit, admin_user, monkeypatch, api_url):
    monkeypatch.setattr(BrowserView, 'limit', 1)
    for name in ['alpha.bin', 'bravo.bin']:
        FileModel.objects.create_from_upload(
            ambit,
            SimpleUploadedFile(name, b'\x00' * 10, content_type='application/octet-stream'),
            folder=ambit.root_folder,
            owner=admin_user,
        )

    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list')
    payload = response.json()
    assert [entry['name'] for entry in payload['files']] == ['alpha.bin']
    assert payload['offset'] == 1

    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/list?offset=1')
    payload = response.json()
    assert [entry['name'] for entry in payload['files']] == ['bravo.bin']
    assert payload['offset'] is None


def test_list_without_upload_permission(staff_client, ambit, sub_folder, api_url):
    response = staff_client.get(f'{api_url}{sub_folder.id}/list')
    assert response.status_code == 200
    assert response.json()['has_upload_permission'] is False


def test_search_without_query(admin_client, ambit, api_url):
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/search')
    assert response.status_code == 400


def test_search_files(admin_client, ambit, uploaded_file, api_url):
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/search?q=small')
    assert response.status_code == 200
    payload = response.json()
    assert payload['offset'] is None
    assert [entry['id'] for entry in payload['files']] == [str(uploaded_file.id)]

    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/search?q=nothing-matches')
    assert response.json()['files'] == []


def test_search_in_descendant_folders(admin_client, ambit, admin_user, sub_folder, api_url):
    nested_file = FileModel.objects.create_from_upload(
        ambit,
        SimpleUploadedFile('needle.bin', b'\x00' * 10, content_type='application/octet-stream'),
        folder=sub_folder,
        owner=admin_user,
    )
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/search?q=needle')
    assert [entry['id'] for entry in response.json()['files']] == [str(nested_file.id)]

    # searching from within the subfolder does not find files of the parent folder
    response = admin_client.get(f'{api_url}{sub_folder.id}/search?q=needle')
    assert [entry['id'] for entry in response.json()['files']] == [str(nested_file.id)]


def test_search_everywhere(admin_client, ambit, uploaded_file, sub_folder, api_url):
    """With the search zone set to “everywhere”, the search starts at the root folder."""
    response = admin_client.get(f'{api_url}{sub_folder.id}/search?q=small')
    assert response.json()['files'] == []

    admin_client.cookies['django-finder-search-zone'] = 'everywhere'
    response = admin_client.get(f'{api_url}{sub_folder.id}/search?q=small')
    assert [entry['id'] for entry in response.json()['files']] == [str(uploaded_file.id)]


def test_search_paginated(admin_client, ambit, admin_user, monkeypatch, api_url):
    monkeypatch.setattr(BrowserView, 'limit', 1)
    for name in ['needle-one.bin', 'needle-two.bin']:
        FileModel.objects.create_from_upload(
            ambit,
            SimpleUploadedFile(name, b'\x00' * 10, content_type='application/octet-stream'),
            folder=ambit.root_folder,
            owner=admin_user,
        )
    response = admin_client.get(f'{api_url}{ambit.root_folder.id}/search?q=needle')
    payload = response.json()
    assert payload['offset'] == 1
    assert len(payload['files']) == 1


def test_upload_file(admin_client, ambit, api_url):
    upload_file = SimpleUploadedFile('uploaded.bin', b'\x00' * 100, content_type='application/octet-stream')
    response = admin_client.post(
        f'{api_url}{ambit.root_folder.id}/upload',
        {'upload_file': upload_file},
        content_type=MULTIPART,
    )
    assert response.status_code == 200
    payload = response.json()
    file_obj = FileModel.objects.get(name='uploaded.bin')
    assert payload['file_info']['id'] == str(file_obj.id)
    assert payload['file_info']['file_size'] == 100
    assert '<input type="text" name="name" value="uploaded.bin"' in payload['form_html']


def test_upload_image(admin_client, ambit, api_url):
    buffer = BytesIO()
    Image.new('RGB', (60, 40)).save(buffer, format='PNG')
    upload_file = SimpleUploadedFile('uploaded.png', buffer.getvalue(), content_type='image/png')
    response = admin_client.post(
        f'{api_url}{ambit.root_folder.id}/upload',
        {'upload_file': upload_file},
        content_type=MULTIPART,
    )
    assert response.status_code == 200
    image_obj = PILImageModel.objects.get(name='uploaded.png')
    assert image_obj.width == 60
    assert image_obj.height == 40
    # the image specific form offers the alternative text
    assert 'name="alt_text"' in response.json()['form_html']


def test_upload_with_invalid_encoding(admin_client, ambit, api_url):
    response = admin_client.post(
        f'{api_url}{ambit.root_folder.id}/upload',
        content_type='application/json',
        data={},
    )
    assert response.status_code == 400


def test_upload_into_missing_folder(admin_client, ambit, missing_inode_id, api_url):
    upload_file = SimpleUploadedFile('uploaded.bin', b'\x00' * 10, content_type='application/octet-stream')
    response = admin_client.post(
        f'{api_url}{missing_inode_id}/upload',
        {'upload_file': upload_file},
        content_type=MULTIPART,
    )
    assert response.status_code == 404


def test_upload_without_write_permission(staff_client, ambit, sub_folder, api_url):
    upload_file = SimpleUploadedFile('uploaded.bin', b'\x00' * 10, content_type='application/octet-stream')
    response = staff_client.post(
        f'{api_url}{sub_folder.id}/upload',
        {'upload_file': upload_file},
        content_type=MULTIPART,
    )
    # Django's PermissionDenied is not a builtin PermissionError, so `dispatch()` maps it to 400 rather than 403.
    assert response.status_code == 400
    assert FileModel.objects.filter(name='uploaded.bin').exists() is False


def test_change_file(admin_client, ambit, uploaded_file, api_url):
    tag = FileTag.objects.create(ambit=ambit, label="Red", color='#ff0000')
    response = admin_client.post(
        f'{api_url}{uploaded_file.id}/change',
        {'name': "renamed.bin", 'tags': [tag.id]},
        content_type=MULTIPART,
    )
    assert response.status_code == 200
    assert response.json()['file_info']['name'] == "renamed.bin"
    uploaded_file.refresh_from_db()
    assert uploaded_file.name == "renamed.bin"
    assert list(uploaded_file.tags.all()) == [tag]


def test_change_file_with_invalid_data(admin_client, ambit, uploaded_file, api_url):
    response = admin_client.post(
        f'{api_url}{uploaded_file.id}/change',
        {'name': ""},
        content_type=MULTIPART,
    )
    assert response.status_code == 200
    payload = response.json()
    assert 'file_info' not in payload
    assert "This field is required." in payload['form_html']
    uploaded_file.refresh_from_db()
    assert uploaded_file.name == 'small_file.bin'


def test_change_file_with_invalid_encoding(admin_client, ambit, uploaded_file, api_url):
    response = admin_client.post(
        f'{api_url}{uploaded_file.id}/change',
        content_type='application/json',
        data={},
    )
    assert response.status_code == 400


def test_change_missing_file(admin_client, ambit, missing_inode_id, api_url):
    response = admin_client.post(
        f'{api_url}{missing_inode_id}/change',
        {'name': "renamed.bin"},
        content_type=MULTIPART,
    )
    assert response.status_code == 404


def test_delete_file(admin_client, ambit, uploaded_file, api_url):
    response = admin_client.delete(f'{api_url}{uploaded_file.id}/change')
    assert response.status_code == 200
    assert response.json() == {'file_info': None}
    assert FileModel.objects.filter(id=uploaded_file.id).exists() is False


def test_crop_image(admin_client, ambit, uploaded_image, api_url):
    response = admin_client.post(f'{api_url}{uploaded_image.id}/crop', {'width': 120, 'height': 60})
    assert response.status_code == 200
    payload = response.json()
    assert payload['image_id'] == str(uploaded_image.id)
    assert payload['width'] == 120
    assert payload['height'] == 60
    assert payload['meta_data']['orig_width'] == 640
    assert payload['meta_data']['orig_height'] == 480
    cropped_path = f'{uploaded_image.id}/{uploaded_image.get_cropped_filename(120, 60)}'
    assert ambit.sample_storage.exists(cropped_path)
    assert payload['cropped_image_url'] == ambit.sample_storage.url(cropped_path)

    # a second request reuses the already generated sample
    response = admin_client.post(f'{api_url}{uploaded_image.id}/crop', {'width': 120, 'height': 60})
    assert response.status_code == 200


def test_crop_image_with_single_dimension(admin_client, ambit, uploaded_image, api_url):
    response = admin_client.post(f'{api_url}{uploaded_image.id}/crop', {'width': 320})
    assert response.json()['height'] == 240

    response = admin_client.post(f'{api_url}{uploaded_image.id}/crop', {'height': 240})
    assert response.json()['width'] == 320


def test_crop_image_without_dimensions(admin_client, ambit, uploaded_image, api_url):
    response = admin_client.post(f'{api_url}{uploaded_image.id}/crop', {})
    assert response.status_code == 422
    assert json.loads(response.content) == {'error': ["At least one of width or height must be given."]}


def test_crop_non_image_file(admin_client, ambit, uploaded_file, api_url):
    response = admin_client.post(f'{api_url}{uploaded_file.id}/crop', {'width': 120})
    assert response.status_code == 404
