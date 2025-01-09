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
    with open(settings.BASE_DIR / 'workdir/assets/demo_image.png', 'rb') as file_handle:
        response = admin_client.post(
            f'{admin_url}/upload',
            {'upload_file': file_handle, 'filename': 'demo_image.png'},
            content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
        )
        file_handle.seek(0)
        while chunk := file_handle.read(4096):
            sha1.update(chunk)
    assert response.status_code == 200
    file_info = response.json()['file_info']
    id = file_info['id']
    assert file_info['name'] == 'demo_image.png'
    assert file_info['file_size'] == os.stat(settings.BASE_DIR / 'workdir/assets/demo_image.png').st_size
    assert file_info['sha1'] == sha1.hexdigest()
    assert file_info['mime_type'] == 'image/png'
    filer_public = filer_settings.FILER_STORAGES['public']['main']['UPLOAD_TO_PREFIX']
    assert file_info['download_url'] == f'{settings.MEDIA_URL}{filer_public}/{id[0:2]}/{id[2:4]}/{id}/demo_image.png'
    filer_public_thumbnails = filer_settings.FILER_STORAGES['public']['thumbnails']['THUMBNAIL_OPTIONS']['base_dir']
    assert file_info['thumbnail_url'] == f'{settings.MEDIA_URL}{filer_public_thumbnails}/{id[0:2]}/{id[2:4]}/{id}/demo_image__180x180.png'
    assert ImageFileModel.objects.filter(id=id).exists()

    # with wrong method
    response = admin_client.get(admin_url + '/upload')
    assert response.status_code == 405

    # with wrong encoding
    response = admin_client.post(admin_url + '/upload', content_type='application/json')
    assert response.status_code == 415

    # with missing folder
    missing_folder_id = uuid5(NAMESPACE_DNS, 'missing-folder')
    response = admin_client.post(
        reverse('admin:finder_inodemodel_change', kwargs={'inode_id': missing_folder_id}) + '/upload',
    )
    assert response.status_code == 404


@pytest.fixture
def uploaded_image(realm, admin_user):
    file_name = 'demo_image.png'
    with open(settings.BASE_DIR / 'workdir/assets' / file_name, 'rb') as file_handle:
        uploaded_file = SimpleUploadedFile(file_name, file_handle.read(), content_type='image/png')
    return ImageFileModel.objects.create_from_upload(
        uploaded_file,
        folder=realm.root_folder,
        owner=admin_user,
    )


@pytest.fixture
def sub_folder(realm, admin_user):
    return FolderModel.objects.create(
        parent=realm.root_folder,
        name='Sub Folder',
        owner=admin_user,
    )


@pytest.mark.django_db
def test_folder_fetch(realm, uploaded_image, admin_client):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id})
    response = admin_client.get(f'{admin_url}/fetch')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    assert ImageFileModel.objects.filter(parent=realm.root_folder, id=inodes[0]['id']).exists()

    # found using search query
    response = admin_client.get(f'{admin_url}/fetch?q=demo')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    assert ImageFileModel.objects.filter(parent=realm.root_folder, id=inodes[0]['id']).exists()

    # not found using search query
    response = admin_client.get(f'{admin_url}/fetch?q=nemo')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    assert len(inodes) == 0

    # with missing folder
    missing_folder_id = uuid5(NAMESPACE_DNS, 'missing-folder')
    response = admin_client.get(
        reverse('admin:finder_inodemodel_change', kwargs={'inode_id': missing_folder_id}) + '/fetch',
    )
    assert response.status_code == 404

    # with wrong method
    response = admin_client.head(f'{admin_url}/fetch')
    assert response.status_code == 405


@pytest.fixture
def update_inode_url(realm):
    return reverse('admin:finder_inodemodel_change', kwargs={'inode_id': realm.root_folder.id}) + '/update'


@pytest.mark.django_db
def test_update_inode_nothing_changed(update_inode_url, uploaded_image, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_image.id), 'name': 'demo_image.png'},
        content_type='application/json',
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_update_inode_update_filename(update_inode_url, uploaded_image, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_image.id), 'name': 'renamed_image.png'},
        content_type='application/json',
    )
    assert response.status_code == 200
    uploaded_image.refresh_from_db()
    assert uploaded_image.name == 'renamed_image.png'


@pytest.mark.django_db
def test_update_inode_update_using_invalid_filename(update_inode_url, uploaded_image, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_image.id), 'name': 'invalid:name'},
        content_type='application/json',
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_update_inode_using_existing_folder_name(update_inode_url, uploaded_image, sub_folder, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_image.id), 'name': "Sub Folder"},
        content_type='application/json',
    )
    assert response.status_code == 409


@pytest.mark.django_db
def test_update_inode_rename_folder(update_inode_url, sub_folder, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(sub_folder.id), 'name': "Renamed Folder"},
        content_type='application/json',
    )
    assert response.status_code == 200
    sub_folder.refresh_from_db()
    assert sub_folder.name == "Renamed Folder"


@pytest.mark.django_db
def test_update_inode_update_with_missing_content_type(update_inode_url, uploaded_image, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_image.id), 'name': 'renamed_image.png'},
    )
    assert response.status_code == 415


@pytest.mark.django_db
def test_update_inode_update_with_missing_folder(admin_client):
    missing_folder_id = uuid5(NAMESPACE_DNS, 'missing-folder')
    response = admin_client.post(
        reverse('admin:finder_inodemodel_change', kwargs={'inode_id': missing_folder_id}) + '/update',
        content_type='application/json',
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_inode_update_with_missing_file(update_inode_url, admin_client):
    missing_file_id = uuid5(NAMESPACE_DNS, 'missing-file')
    response = admin_client.post(
        update_inode_url,
        {'id': str(missing_file_id)},
        content_type='application/json',
    )
    assert response.status_code == 404


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

    # with missing Content-Type
    response = admin_client.post(f'{admin_url}/add_folder')
    assert response.status_code == 415

    # add a second folder with the same name
    response = admin_client.post(f'{admin_url}/add_folder', {'name': "Sub Folder"}, content_type='application/json')
    assert response.status_code == 409
    assert response.content.decode() == "A folder named “Sub Folder” already exists."
