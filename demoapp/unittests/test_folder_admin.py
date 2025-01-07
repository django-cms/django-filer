import json
import os
from uuid import uuid5, NAMESPACE_DNS

import hashlib
import pytest

from bs4 import BeautifulSoup

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from filer import settings as filer_settings
from finder.contrib.image.models import ImageFileModel
from finder.models.folder import FolderModel
from finder.models.realm import RealmModel


@pytest.mark.django_db
def test_create_realm_on_first_access(admin_client):
    assert RealmModel.objects.exists() is False
    response = admin_client.get(reverse('admin:finder_foldermodel_changelist'))
    assert response.status_code == 302
    realm = RealmModel.objects.first()
    assert realm is not None
    redirected = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id})
    assert response.url == redirected
    assert realm.root_folder.is_folder is True
    assert realm.root_folder.is_trash is False
    assert realm.root_folder.owner == response.wsgi_request.user
    assert realm.root_folder.name == '__root__'
    assert realm.root_folder.parent is None
    assert realm.root_folder.is_root
    assert realm.trash_folders.count() == 0


@pytest.mark.django_db
def test_access_root_folder(realm, admin_client):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id})
    response = admin_client.get(admin_url)
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, 'html.parser')
    assert soup.title.string == "Root | Change Folder | Django site admin"
    script_element = soup.find(id='finder-settings')
    assert script_element.name == 'script'
    finder_settings = json.loads(script_element.string)
    finder_settings.pop('csrf_token')
    finder_settings.pop('favorite_folders')
    finder_settings.pop('menu_extensions')
    assert finder_settings == {
        'name': '__root__',
        'is_folder': True,
        'folder_id': str(realm.root_folder.id),
        'parent_id': None,
        'parent_url': None,
        'is_root': True,
        'is_trash': False,
        'folder_url': admin_url,
        'base_url': reverse('admin:finder_foldermodel_changelist'),
        'ancestors': [str(realm.root_folder.id)],
    }


@pytest.mark.django_db
def test_access_folder_not_found(admin_client):
    not_inode_id = uuid5(NAMESPACE_DNS, 'not-found')
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': not_inode_id})
    response = admin_client.get(admin_url)
    assert response.status_code == 404



@pytest.mark.django_db
def test_folder_upload_file(realm, admin_client):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id})
    sha1 = hashlib.sha1()
    with open(settings.BASE_DIR / 'workdir/assets/image_0.png', 'rb') as file_handle:
        response = admin_client.post(
            f'{admin_url}/upload',
            {'upload_file': file_handle, 'filename': 'image_0.png'},
            content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
        )
        file_handle.seek(0)
        while chunk := file_handle.read(4096):
            sha1.update(chunk)
    assert response.status_code == 200
    file_info = response.json()['file_info']
    id = file_info['id']
    assert file_info['name'] == 'image_0.png'
    assert file_info['file_size'] == os.stat(settings.BASE_DIR / 'workdir/assets/image_0.png').st_size
    assert file_info['sha1'] == sha1.hexdigest()
    assert file_info['mime_type'] == 'image/png'
    filer_public = filer_settings.FILER_STORAGES['public']['main']['UPLOAD_TO_PREFIX']
    assert file_info['download_url'] == f'{settings.MEDIA_URL}{filer_public}/{id[0:2]}/{id[2:4]}/{id}/image_0.png'
    filer_public_thumbnails = filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    assert file_info['thumbnail_url'] == f'{settings.MEDIA_URL}{filer_public_thumbnails}/{id[0:2]}/{id[2:4]}/{id}/image_0__180x180.png'
    assert ImageFileModel.objects.filter(id=id).exists()


@pytest.fixture
def uploaded_images(realm, admin_user):
    images = []
    for counter in range(10):
        file_name = f'image_{counter}.png'
        with open(settings.BASE_DIR / f'workdir/assets/{file_name}', 'rb') as file_handle:
            uploaded_file = SimpleUploadedFile(file_name, file_handle.read(), content_type='image/png')
        images.append(
            ImageFileModel.objects.create_from_upload(
                uploaded_file,
                folder=realm.root_folder,
                owner=admin_user,
            )
        )
    return images


@pytest.mark.django_db
def test_folder_fetch(realm, uploaded_images, admin_client):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id})
    response = admin_client.get(f'{admin_url}/fetch')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    image_ids = {str(im.id) for im in ImageFileModel.objects.all()}
    assert {inode['id'] for inode in inodes} == image_ids


@pytest.mark.django_db
def test_create_sub_folder(realm, admin_client):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id})
    response = admin_client.post(f'{admin_url}/add_folder', {'name': "Sub Folder"}, content_type='application/json')
    assert response.status_code == 200
    new_folder = response.json()['new_folder']
    assert new_folder['name'] == "Sub Folder"
    sub_folder = FolderModel.objects.get(id=new_folder['id'])
    response = admin_client.get(f'{admin_url}/fetch')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    assert inodes[0]['id'] == str(sub_folder.id)
    assert inodes[0]['name'] == "Sub Folder"
    assert inodes[0]['is_folder'] is True
    assert inodes[0]['parent'] == str(realm.root_folder.id)
    assert inodes[0]['thumbnail_url'] == f'{settings.STATIC_URL}filer/icons/folder.svg'

    # with missing content-type
    response = admin_client.post(f'{admin_url}/add_folder')
    assert response.status_code == 400

    # add a second folder with the same name
    response = admin_client.post(f'{admin_url}/add_folder', {'name': "Sub Folder"}, content_type='application/json')
    assert response.status_code == 409
    assert response.content.decode() == "A folder named “Sub Folder” already exists."
