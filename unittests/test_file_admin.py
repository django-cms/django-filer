import json
import pytest

from bs4 import BeautifulSoup
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.models.file import FileModel
from finder.models.permission import AccessControlEntry, Privilege


def test_replace_file(admin_client, ambit, uploaded_file, missing_inode_id):
    """Test replacing the content of an existing file via the FileAdmin upload endpoint."""
    base_url = reverse('admin:finder_filemodel_changelist')
    upload_url = f'{base_url}{uploaded_file.id}/upload'
    original_file_size = uploaded_file.file_size
    original_sha1 = uploaded_file.sha1

    # Successful replacement with same mime type
    replacement_content = b'\x00' * 2000
    replacement_file = SimpleUploadedFile('replacement.bin', replacement_content, content_type='application/octet-stream')
    response = admin_client.post(
        upload_url,
        {'upload_file': replacement_file},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 200
    uploaded_file.refresh_from_db()
    assert uploaded_file.file_size == len(replacement_content)
    assert uploaded_file.file_size != original_file_size
    assert uploaded_file.sha1 != original_sha1

    # Wrong HTTP method
    response = admin_client.get(upload_url)
    assert response.status_code == 400

    # File not found
    missing_url = f'{base_url}{missing_inode_id}/upload'
    replacement_file = SimpleUploadedFile('replacement.bin', b'\x00', content_type='application/octet-stream')
    response = admin_client.post(
        missing_url,
        {'upload_file': replacement_file},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 404

    # Wrong content type (not multipart)
    response = admin_client.post(upload_url, content_type='application/json')
    assert response.status_code == 400

    # Mime type mismatch
    wrong_mime_file = SimpleUploadedFile('image.png', b'\x89PNG\r\n', content_type='image/png')
    response = admin_client.post(
        upload_url,
        {'upload_file': wrong_mime_file},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 400


@pytest.fixture(params=['user', 'group', 'everyone'])
def read_only_principal(admin_user, request):
    admin_user.is_superuser = False
    admin_user.save(update_fields=['is_superuser'])
    if request.param == 'user':
        return {'user': admin_user, 'privilege': Privilege.READ}
    if request.param == 'group':
        group = admin_user.groups.create(name='Test Group')
        admin_user.groups.add(group)
        return {'group': group, 'privilege': Privilege.READ}
    if request.param == 'everyone':
        return {'privilege': Privilege.READ}


def test_replace_file_without_write_permission(admin_client, admin_user, ambit, uploaded_file, read_only_principal):
    """Test that replacing a file fails when the user only has read permission."""
    base_url = reverse('admin:finder_filemodel_changelist')
    upload_url = f'{base_url}{uploaded_file.id}/upload'
    original_file_size = uploaded_file.file_size
    original_sha1 = uploaded_file.sha1

    # Assign read-only permission on the file
    AccessControlEntry.objects.all().delete()
    AccessControlEntry.objects.create(inode=uploaded_file.id, **read_only_principal)

    # Attempt to replace the file
    replacement_content = b'\x00' * 2000
    replacement_file = SimpleUploadedFile('replacement.bin', replacement_content, content_type='application/octet-stream')
    response = admin_client.post(
        upload_url,
        {'upload_file': replacement_file},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 403

    # Verify the file content was not changed
    uploaded_file.refresh_from_db()
    assert uploaded_file.file_size == original_file_size
    assert uploaded_file.sha1 == original_sha1


def test_file_detail_view(admin_client, admin_user, ambit, uploaded_file):
    """Test the change view of an uploaded file renders expected HTML elements."""
    model_admin = admin.site._registry[FileModel]
    admin_url = model_admin.get_inode_url(ambit.slug, str(uploaded_file.id))
    response = admin_client.get(admin_url)
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, 'html.parser')

    # Page title
    assert soup.title.string == f"{uploaded_file.name} | Change File | Django site admin"

    # Breadcrumbs contain links to Home, Finder, parent folder, and file name
    breadcrumbs = soup.find(class_='breadcrumbs')
    assert breadcrumbs is not None
    links = breadcrumbs.find_all('a')
    assert links[0].string.strip() == "Home"
    assert links[1].string.strip() == "Finder"
    assert uploaded_file.name in breadcrumbs.get_text()

    # Form with file fields
    form = soup.find('form', id='filemodel_form')
    assert form is not None
    assert form.get('method') == 'post'

    # Name input field
    name_input = soup.find('input', {'id': 'id_name'})
    assert name_input is not None
    assert name_input.get('value') == uploaded_file.name

    # React mount point
    content_react = soup.find('div', id='content-react')
    assert content_react is not None

    # finder-settings script element with JSON context
    script_element = soup.find(id='finder-settings')
    assert script_element is not None
    assert script_element.name == 'script'
    finder_settings = json.loads(script_element.string)
    assert finder_settings['name'] == uploaded_file.name
    assert finder_settings['is_folder'] is False
    assert finder_settings['file_id'] == str(uploaded_file.id)
    assert finder_settings['file_mime_type'] == uploaded_file.mime_type
    assert finder_settings['filename'] == uploaded_file.file_name
    assert 'download_url' in finder_settings
    assert 'thumbnail_url' in finder_settings
    assert 'csrf_token' in finder_settings
    assert finder_settings['can_change'] is True
    assert finder_settings['folder_id'] == str(uploaded_file.parent_id)
