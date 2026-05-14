import pytest
from io import BytesIO

from enum import Enum, auto
from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.models.permission import AccessControlEntry, Privilege


class AccessControl(Enum):
    ALLOW = auto()
    READ_ONLY = auto()


@pytest.mark.parametrize('access_control', [AccessControl.ALLOW, AccessControl.READ_ONLY, None])
def test_replace_image(admin_client, admin_user, ambit, uploaded_image, missing_inode_id, access_control, principal_kwargs):
    base_url = reverse('admin:finder_filemodel_changelist')
    upload_url = f'{base_url}{uploaded_image.id}/upload'
    original_sha1 = uploaded_image.sha1
    new_image = Image.new('RGB', (960, 960), color=(128, 128, 128))

    if admin_user.is_superuser:
        if access_control is not None:
            return  # skip redundant test cases where superuser has access regardless of ACL
    else:
        AccessControlEntry.objects.all().delete()
        if access_control == AccessControl.ALLOW:
            AccessControlEntry.objects.create(inode=uploaded_image.id, **principal_kwargs)
        elif access_control == AccessControl.READ_ONLY:
            principal_kwargs['privilege'] = Privilege.READ
            AccessControlEntry.objects.create(inode=uploaded_image.id, **principal_kwargs)

    # replace image with same MIME type
    buffer = BytesIO()
    new_image.save(buffer, format='PNG')
    replacement_image = SimpleUploadedFile('grey.png', buffer.getvalue(), content_type='image/png')
    response = admin_client.post(
        upload_url,
        {'upload_file': replacement_image},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    if admin_user.is_superuser or access_control == AccessControl.ALLOW:
        assert response.status_code == 200
    else:
        assert response.status_code == 403
        return

    uploaded_image.refresh_from_db()
    assert uploaded_image.file_size == buffer.tell()
    assert uploaded_image.sha1 != original_sha1
    original_sha1 = uploaded_image.sha1
    assert uploaded_image.width == 960
    assert uploaded_image.height == 960

    # replace image with alternative MIME type
    buffer = BytesIO()
    new_image.save(buffer, format='JPEG')
    replacement_image = SimpleUploadedFile('grey.jpeg', buffer.getvalue(), content_type='image/jpeg')
    response = admin_client.post(
        upload_url,
        {'upload_file': replacement_image},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 400
    assert response.text == "Can not replace file test_image.png with different mime type."
    uploaded_image.refresh_from_db()
    assert uploaded_image.sha1 == original_sha1
    assert uploaded_image.width == 960
    assert uploaded_image.height == 960
