import json
import pytest
from io import BytesIO

from PIL import Image, ImageDraw
from bs4 import BeautifulSoup
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.models.file import FileModel
from finder.models.permission import AccessControlEntry, Privilege


def test_replace_image(admin_client, ambit, uploaded_image, missing_inode_id):
    base_url = reverse('admin:finder_filemodel_changelist')
    upload_url = f'{base_url}{uploaded_image.id}/upload'
    original_sha1 = uploaded_image.sha1
    new_image = Image.new('RGB', (960, 960), color=(128, 128, 128))

    # replace image with same MIME type
    buffer = BytesIO()
    new_image.save(buffer, format='PNG')
    replacement_image = SimpleUploadedFile('grey.png', buffer.getvalue(), content_type='image/png')
    response = admin_client.post(
        upload_url,
        {'upload_file': replacement_image},
        content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
    )
    assert response.status_code == 200
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
