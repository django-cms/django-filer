import pytest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

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

