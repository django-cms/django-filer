import json
import hashlib
import pytest

from bs4 import BeautifulSoup
from enum import Enum, auto

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT
from django.urls import reverse

from finder.models.file import FileModel
from finder.models.folder import FolderModel, PinnedFolder, ROOT_FOLDER_NAME
from finder.models.inode import DiscardedInode
from finder.models.filetag import FileTag
from finder.models.permission import AccessControlEntry, Privilege


def test_root_folder_exists(admin_client, ambit):
    base_url = reverse('admin:app_list', kwargs={'app_label': 'finder'})
    response = admin_client.get(f'{base_url}{ambit.slug}/')
    assert response.status_code == 301
    assert response.url == f'{base_url}{ambit.slug}/{ambit.root_folder_id}'
    assert ambit.root_folder.is_folder is True
    assert ambit.root_folder.is_trash is False
    assert ambit.root_folder.owner is None
    assert ambit.root_folder.name == ROOT_FOLDER_NAME
    assert ambit.root_folder.parent is None
    assert ambit.root_folder.is_root is True
    assert ambit.trash_folders.count() == 0


def test_access_root_folder(admin_client, root_folder_url, ambit):
    response = admin_client.get(root_folder_url)
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
        'name': ROOT_FOLDER_NAME,
        'is_folder': True,
        'folder_id': str(ambit.root_folder.id),
        'parent_id': None,
        'parent_url': None,
        'is_root': True,
        'is_trash': False,
        'folder_url': root_folder_url,
        'is_admin': True,
        'can_change': True,
        'base_url': reverse('admin:finder_foldermodel_changelist'),
        'ancestors': [{'id': str(ambit.root_folder.id), 'can_change': True, 'can_view': True}],
        'open_folder_icon_url': staticfiles_storage.url('finder/icons/folder-open.svg'),
    }


def test_access_folder_not_found(admin_client, ambit, missing_inode_id):
    base_url = reverse('admin:app_list', kwargs={'app_label': 'finder'})
    response = admin_client.get(f'{base_url}{ambit.slug}/{missing_inode_id}')
    assert response.status_code == 404


@pytest.mark.parametrize('binary_file', ['small_file.bin', 'huge_file.bin'])
def test_folder_upload_file(admin_client, ambit, binary_file, missing_inode_id):
    sha1 = hashlib.sha1()
    base_url = reverse('admin:finder_inodemodel_change', args=(ambit.root_folder.id,))
    with open(settings.BASE_DIR / 'workdir/assets' / binary_file, 'rb') as file_handle:
        response = admin_client.post(
            f'{base_url}/upload',
            {'upload_file': file_handle, 'filename': binary_file},
            content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
        )
        file_handle.seek(0)
        while chunk := file_handle.read(4096):
            sha1.update(chunk)
    assert response.status_code == 200
    file_info = response.json()['file_info']
    assert file_info['name'] == binary_file
    assert FileModel.objects.filter(id=file_info['id']).exists()
    assert file_info['file_size'] == ambit.original_storage.size('{id}/{name}'.format(**file_info))
    assert file_info['sha1'] == sha1.hexdigest()
    assert file_info['mime_type'] == 'application/octet-stream'
    assert file_info['download_url'] == ambit.original_storage.url('{id}/{name}'.format(**file_info))
    assert file_info['thumbnail_url'] == f'{settings.STATIC_URL}finder/icons/file-unknown.svg'

    # with wrong method
    response = admin_client.get(f'{base_url}/upload')
    assert response.status_code == 405

    # with wrong encoding
    response = admin_client.post(f'{base_url}/upload', content_type='application/json')
    assert response.status_code == 415

    # with missing folder
    base_url = reverse('admin:finder_inodemodel_change', args=(missing_inode_id,))
    with open(settings.BASE_DIR / 'workdir/assets' / binary_file, 'rb') as file_handle:
        response = admin_client.post(
            f'{base_url}/upload',
            {'upload_file': file_handle, 'filename': binary_file},
            content_type=MULTIPART_CONTENT % {'boundary': 'BoUnDaRyStRiNg'},
        )
        file_handle.seek(0)
    assert response.status_code == 404


@pytest.fixture
def uploaded_file(ambit, admin_user):
    file_name = 'small_file.bin'
    with open(settings.BASE_DIR / 'workdir/assets' / file_name, 'rb') as file_handle:
        uploaded_file = SimpleUploadedFile(file_name, file_handle.read(), content_type='application/octet-stream')
    return FileModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=ambit.root_folder,
        owner=admin_user,
    )


@pytest.fixture
def sub_folder(ambit, admin_user):
    return FolderModel.objects.create(
        parent=ambit.root_folder,
        name='Sub Folder',
        owner=admin_user,
    )


@pytest.mark.django_db
def test_folder_fetch(ambit, uploaded_file, admin_client, missing_inode_id):
    base_url = reverse('admin:finder_inodemodel_change', args=(ambit.root_folder_id,))
    response = admin_client.get(f'{base_url}/fetch')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    assert FileModel.objects.filter(parent=ambit.root_folder, id=inodes[0]['id']).exists()

    # found using search query
    response = admin_client.get(f'{base_url}/fetch?q=small')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    assert FileModel.objects.filter(parent=ambit.root_folder, id=inodes[0]['id']).exists()

    # not found using search query
    response = admin_client.get(f'{base_url}/fetch?q=foobar')
    assert response.status_code == 200
    inodes = response.json()['inodes']
    assert len(inodes) == 0

    # with missing folder
    missing_folder_url = reverse('admin:finder_inodemodel_change', args=(missing_inode_id,))
    response = admin_client.get(f'{missing_folder_url}/fetch')
    assert response.status_code == 404

    # with wrong method
    response = admin_client.head(f'{base_url}/fetch')
    assert response.status_code == 405


@pytest.fixture
def update_inode_url(ambit):
    return reverse('admin:finder_inodemodel_change', kwargs={'inode_id': ambit.root_folder.id}) + '/update'


def test_update_inode_change_nothing(update_inode_url, uploaded_file, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_file.id), 'name': uploaded_file.name},
        content_type='application/json',
    )
    assert response.status_code == 200


def test_update_inode_rename_file(update_inode_url, uploaded_file, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_file.id), 'name': "renamed_file.bin"},
        content_type='application/json',
    )
    assert response.status_code == 200
    uploaded_file.refresh_from_db()
    assert uploaded_file.name == "renamed_file.bin"


def test_update_inode_update_using_invalid_filename(update_inode_url, uploaded_file, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_file.id), 'name': 'invalid:name'},
        content_type='application/json',
    )
    assert response.status_code == 409


def test_update_inode_using_existing_folder_name(update_inode_url, uploaded_file, sub_folder, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_file.id), 'name': "Sub Folder"},
        content_type='application/json',
    )
    assert response.status_code == 409


def test_update_inode_rename_folder(update_inode_url, sub_folder, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(sub_folder.id), 'name': "Renamed Folder"},
        content_type='application/json',
    )
    assert response.status_code == 200
    sub_folder.refresh_from_db()
    assert sub_folder.name == "Renamed Folder"


def test_update_inode_update_with_missing_content_type(update_inode_url, uploaded_file, admin_client):
    response = admin_client.post(
        update_inode_url,
        {'id': str(uploaded_file.id), 'name': 'renamed_file.bin'},
    )
    assert response.status_code == 415


def test_update_inode_update_with_missing_folder(admin_client, missing_inode_id):
    response = admin_client.post(
        reverse('admin:finder_inodemodel_change', kwargs={'inode_id': missing_inode_id}) + '/update',
        content_type='application/json',
    )
    assert response.status_code == 404


def test_update_inode_update_with_missing_file(update_inode_url, admin_client, missing_inode_id):
    response = admin_client.post(
        update_inode_url,
        {'id': str(missing_inode_id)},
        content_type='application/json',
    )
    assert response.status_code == 404


def test_create_sub_folder(admin_client, ambit):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': ambit.root_folder.id})
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
    assert inodes[0]['parent'] == str(ambit.root_folder.id)
    assert inodes[0]['thumbnail_url'] == f'{settings.STATIC_URL}finder/icons/folder.svg'

    # with missing Content-Type
    response = admin_client.post(f'{admin_url}/add_folder')
    assert response.status_code == 415

    # add a second folder with the same name
    response = admin_client.post(f'{admin_url}/add_folder', {'name': "Sub Folder"}, content_type='application/json')
    assert response.status_code == 409
    assert response.content.decode() == "A folder named “Sub Folder” already exists."


def test_move_file_into_subfolder(admin_client, ambit, uploaded_file, sub_folder):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': ambit.root_folder.id})
    response = admin_client.post(
        f'{admin_url}/move',
        json.dumps({'inode_ids': [str(uploaded_file.id)], 'target_id': str(sub_folder.id)}),
        content_type='application/json',
    )
    assert response.status_code == 200
    uploaded_file.refresh_from_db()
    assert uploaded_file.parent == sub_folder


def test_keep_file_in_subfolder(admin_client, ambit, uploaded_file, sub_folder):
    uploaded_file.parent = sub_folder
    uploaded_file.save()
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
    response = admin_client.post(
        f'{admin_url}/move',
        json.dumps({'inode_ids': [str(uploaded_file.id)], 'target_id': str(sub_folder.id)}),
        content_type='application/json',
    )
    assert response.status_code == 200
    uploaded_file.refresh_from_db()
    assert uploaded_file.parent == sub_folder


def test_move_file_to_parent(admin_client, ambit, uploaded_file, sub_folder):
    uploaded_file.parent = sub_folder
    uploaded_file.save()
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
    response = admin_client.post(
        f'{admin_url}/move',
        json.dumps({'inode_ids': [str(uploaded_file.id)], 'target_id': 'parent'}),
        content_type='application/json',
    )
    assert response.status_code == 200
    uploaded_file.refresh_from_db()
    assert uploaded_file.parent == ambit.root_folder


def test_move_file_to_self(admin_client, ambit, uploaded_file, sub_folder):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
    response = admin_client.post(
        f'{admin_url}/move',
        json.dumps({'inode_ids': [str(uploaded_file.id)]}),
        content_type='application/json',
    )
    assert response.status_code == 200
    uploaded_file.refresh_from_db()
    assert uploaded_file.parent == sub_folder


def test_move_file_to_missing_parent(admin_client, ambit, uploaded_file):
    assert uploaded_file.parent == ambit.root_folder
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': ambit.root_folder.id})
    response = admin_client.post(
        f'{admin_url}/move',
        json.dumps({'inode_ids': [str(uploaded_file.id)], 'target_id': 'parent'}),
        content_type='application/json',
    )
    assert response.status_code == 404
    uploaded_file.refresh_from_db()
    assert uploaded_file.parent == ambit.root_folder


def test_move_file_to_missing_inode(admin_client, ambit, uploaded_file, missing_inode_id):
    assert uploaded_file.parent == ambit.root_folder
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': ambit.root_folder.id})
    response = admin_client.post(
        f'{admin_url}/move',
        json.dumps({'inode_ids': [str(uploaded_file.id)], 'target_id': str(missing_inode_id)}),
        content_type='application/json',
    )
    assert response.status_code == 404
    uploaded_file.refresh_from_db()
    assert uploaded_file.parent == ambit.root_folder


class AccessControl(Enum):
    ALLOW = auto()
    SOURCE_DENIED = auto()
    TARGET_DENIED = auto()
    # PARTIAL_DENIED = auto()


@pytest.fixture(params=['superuser', 'user', 'group', 'everyone'])
def principal_kwargs(admin_user, request):
    if request.param == 'superuser':
        return
    admin_user.is_superuser = False
    admin_user.save(update_fields=['is_superuser'])
    if request.param == 'user':
        return {'user': admin_user, 'privilege': Privilege.READ_WRITE}
    if request.param == 'group':
        group = admin_user.groups.create(name='Test Group')
        admin_user.groups.add(group)
        return {'group': group, 'privilege': Privilege.READ_WRITE}
    if request.param == 'everyone':
        return {'everyone': True, 'privilege': Privilege.READ_WRITE}


@pytest.mark.parametrize('access_control', AccessControl)
@pytest.mark.parametrize('same_folder', [True, False])
@pytest.mark.parametrize('finder_layout', ['tiles', 'list'])
def test_reorder_inodes(
    admin_client, admin_user, uploaded_file, sub_folder, principal_kwargs, finder_layout, same_folder, access_control
):
    admin_client.cookies['django-finder-layout'] = finder_layout
    created_inodes = FileModel.objects.bulk_create([
        *(FileModel(
            parent=sub_folder.parent,
            name=f"File #R{ordering}",
            file_size=uploaded_file.file_size,
            sha1=uploaded_file.sha1,
            owner=uploaded_file.owner,
            ordering=ordering,
        ) for ordering in range(1, 10)),
        *(FileModel(
            parent=sub_folder,
            name=f"File #S{ordering}",
            file_size=uploaded_file.file_size,
            sha1=uploaded_file.sha1,
            owner=uploaded_file.owner,
            ordering=ordering,
        ) for ordering in range(1, 10)),
    ])
    AccessControlEntry.objects.all().delete()
    if admin_user.is_superuser is False:
        acl = [
            AccessControlEntry(inode=inode.id, **principal_kwargs)
            for inode in created_inodes
        ]
        acl.pop(14)  # one file is not readable, so it should not be reordered
        if access_control != AccessControl.SOURCE_DENIED:
            acl.append(AccessControlEntry(inode=sub_folder.id, **principal_kwargs))
        if access_control != AccessControl.TARGET_DENIED:
            acl.append(AccessControlEntry(inode=sub_folder.parent.id, **principal_kwargs))
        AccessControlEntry.objects.bulk_create(acl)

    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
    if same_folder:
        target_id = created_inodes[11].id
        expected_root = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
        if admin_user.is_superuser:
            if finder_layout == 'tiles':
                expected_sub = ['S1', 'S2', 'S3', 'S5', 'S6', 'S7', 'S4', 'S8', 'S9']
            else:
                expected_sub = ['S1', 'S2', 'S5', 'S6', 'S7', 'S3', 'S4', 'S8', 'S9']
        else:
            if finder_layout == 'tiles':
                expected_sub = ['S1', 'S2', 'S3', 'S5', 'S7', 'S4', 'S6', 'S8', 'S9']
            else:
                expected_sub = ['S1', 'S2', 'S5', 'S7', 'S3', 'S4', 'S6', 'S8', 'S9']
    else:
        target_id = created_inodes[3].id  # target is in parent folder, so files are moved there
        if admin_user.is_superuser:
            if finder_layout == 'tiles':
                expected_root = ['R1', 'R2', 'R3', 'R4', 'S5', 'S6', 'S7', 'R5', 'R6', 'R7', 'R8', 'R9']
            else:
                expected_root = ['R1', 'R2', 'R3', 'S5', 'S6', 'S7', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
            expected_sub = ['S1', 'S2', 'S3', 'S4', 'S8', 'S9']
        else:
            if finder_layout == 'tiles':
                expected_root = ['R1', 'R2', 'R3', 'R4', 'S5', 'S7', 'R5', 'R6', 'R7', 'R8', 'R9']
            else:
                expected_root = ['R1', 'R2', 'R3', 'S5', 'S7', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
            expected_sub = ['S1', 'S2', 'S3', 'S4', 'S6', 'S8', 'S9']
    response = admin_client.post(
        f'{admin_url}/reorder',
        json.dumps({
            'target_id': str(target_id),
            'inode_ids': [str(created_file.id) for created_file in created_inodes[13:16]]
        }),
        content_type='application/json',
    )
    if (admin_user.is_superuser is False and (
        not same_folder and access_control == AccessControl.TARGET_DENIED
        or same_folder and access_control == AccessControl.SOURCE_DENIED
    )):
        assert response.status_code == 403
        return
    assert response.status_code == 200
    default_access_control_list = set(ace for ace in sub_folder.parent.default_access_control_list.all())
    for file, expected in zip(sub_folder.parent.listdir(name__startswith='File').order_by('ordering'), expected_root):
        assert file['name'] == f"File #{expected}"
        for file in sub_folder.parent.listdir(name__startswith='File #S'):
            # check that default ACL is assigned to inodes moved through reordering
            acl = set(ace for ace in AccessControlEntry.objects.filter(inode=file['id']))
            assert acl == default_access_control_list
    for file, expected in zip(sub_folder.listdir(name__startswith='File').order_by('ordering'), expected_sub):
        assert file['name'] == f"File #{expected}"


@pytest.mark.parametrize('access_control', [AccessControl.ALLOW, AccessControl.SOURCE_DENIED])
def test_delete_inodes(admin_client, admin_user, uploaded_file, sub_folder, principal_kwargs, access_control):
    ambit = sub_folder.get_ambit()
    PinnedFolder.objects.all().delete()
    created_inodes = FileModel.objects.bulk_create([
        FileModel(
            parent=sub_folder,
            name=f"Inode #F{ordering}",
            file_size=uploaded_file.file_size,
            sha1=uploaded_file.sha1,
            owner=uploaded_file.owner,
            ordering=ordering,
        ) for ordering in range(1, 10) if ordering != 5
    ])
    favorite_folder = FolderModel.objects.create(
        parent=sub_folder,
        name="Inode #D5",
        owner=uploaded_file.owner,
        ordering=5,
    )
    created_inodes.insert(4, favorite_folder)
    AccessControlEntry.objects.all().delete()
    if admin_user.is_superuser is False:
        acl = [
            AccessControlEntry(inode=inode.id, **principal_kwargs)
            for inode in created_inodes
        ]
        acl[4].privilege = Privilege.READ  # one file is read-only, so it should not be deleted
        if access_control != AccessControl.SOURCE_DENIED:
            acl.append(AccessControlEntry(inode=sub_folder.id, **principal_kwargs))
        AccessControlEntry.objects.bulk_create(acl)

    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
    response = admin_client.post(
        f'{admin_url}/toggle_pin',
        json.dumps({'pinned_id': str(favorite_folder.id)}),
        content_type='application/json',
    )
    favorite_folders = response.json()['favorite_folders']
    assert len(favorite_folders) == 2
    assert favorite_folders[0] == {
        'id': str(favorite_folder.id),
        'name': "Inode #D5",
        'is_pinned': True,
        'can_change': admin_user.is_superuser,
        'change_url': f'/admin/finder/{ambit.slug}/{favorite_folder.id}',
    }
    for key in ['created_at', 'last_modified_at', 'owner_name', 'download_url', 'thumbnail_url', 'summary']:
        favorite_folders[1].pop(key)
    assert favorite_folders[1] == {
        'id': str(sub_folder.id),
        'name': "Sub Folder",
        'parent': str(ambit.root_folder.id),
        'is_folder': True,
        'is_root': False,
        'change_url': f'/admin/finder/{ambit.slug}/{sub_folder.id}',
    }
    response = admin_client.post(
        f'{admin_url}/delete',
        json.dumps({
            'inode_ids': [str(created_file.id) for created_file in created_inodes[2:6]]
        }),
        content_type='application/json',
    )
    if admin_user.is_superuser is False and access_control != AccessControl.ALLOW:
        assert response.status_code == 403
        return

    assert response.status_code == 200
    favorite_folders = response.json()['favorite_folders']
    if admin_user.is_superuser:
        assert len(favorite_folders) == 2
        assert favorite_folders[1]['is_trash']
    else:
        if access_control == AccessControl.ALLOW:
            assert len(favorite_folders) == 3
            assert favorite_folders[0]['id'] == str(favorite_folder.id)
            assert favorite_folders[2]['is_trash']
    inode_list = sub_folder.listdir(name__startswith="Inode").order_by('ordering')
    if admin_user.is_superuser:
        expected_sub = ['F1', 'F2', 'F7', 'F8', 'F9']
        expected_trash = ['F3', 'F4', 'D5', 'F6']
    else:
        expected_sub = ['F1', 'F2', 'D5', 'F7', 'F8', 'F9']
        expected_trash = ['F3', 'F4', 'F6']
    assert len(inode_list) == len(expected_sub)
    for file, ordering, expected in zip(inode_list, range(1, 6), expected_sub):
        assert file['name'] == f"Inode #{expected}"
        assert file['ordering'] == ordering
        if admin_user.is_superuser is False:
            assert AccessControlEntry.objects.filter(inode=file['id']).exists()

    ambit = sub_folder.get_ambit()
    trash_folder = ambit.trash_folders.get(owner=admin_user)
    deleted_inodes = trash_folder.listdir(name__startswith="Inode").order_by('ordering')
    assert len(deleted_inodes) == len(expected_trash)
    for file, ordering, expected in zip(deleted_inodes, range(1, 5), expected_trash):
        assert file['ordering'] == ordering
        assert not AccessControlEntry.objects.filter(inode=file['id']).exists()
        assert DiscardedInode.objects.get(inode=file['id']).previous_parent == sub_folder


@pytest.mark.parametrize('access_control', [AccessControl.ALLOW, AccessControl.TARGET_DENIED])
def test_copy_inodes(admin_client, admin_user, uploaded_file, sub_folder, principal_kwargs, access_control):
    created_inodes = FileModel.objects.bulk_create([
        FileModel(
            parent=sub_folder,
            name=f"File #S{ordering}",
            file_size=uploaded_file.file_size,
            sha1=uploaded_file.sha1,
            owner=uploaded_file.owner,
            ordering=ordering,
        ) for ordering in range(1, 10)
    ])
    AccessControlEntry.objects.all().delete()
    if admin_user.is_superuser is False:
        principal_kwargs.pop('privilege')
        acl = [
            AccessControlEntry(inode=inode.id, privilege=Privilege.READ, **principal_kwargs)
            for inode in created_inodes
        ]
        acl.pop(4)  # one file is not readable, so it should not be copied
        if access_control != AccessControl.TARGET_DENIED:
            acl.append(AccessControlEntry(
                inode=sub_folder.parent.id,
                privilege=Privilege.READ_WRITE,
                **principal_kwargs
            ))
        AccessControlEntry.objects.bulk_create(acl)

    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.parent.id})
    response = admin_client.post(
        f'{admin_url}/copy',
        json.dumps({
            'inode_ids': [str(created_file.id) for created_file in created_inodes[2:7]]
        }),
        content_type='application/json',
    )
    if admin_user.is_superuser is False and access_control == AccessControl.TARGET_DENIED:
        assert response.status_code == 403
        return

    assert response.status_code == 200
    body = response.json()
    inode_list = sub_folder.listdir(name__startswith='File').order_by('ordering')

    # check that original files are not modified
    assert len(created_inodes) == len(inode_list)
    for created_inode, expected_inode in zip(created_inodes, inode_list):
        assert created_inode.id == expected_inode['id']
        assert created_inode.ordering == expected_inode['ordering']

    if admin_user.is_superuser:
        expected_copied = ['S3', 'S4', 'S5', 'S6', 'S7']
    else:
        expected_copied = ['S3', 'S4', 'S6', 'S7']

    target_inodes = list(sub_folder.parent.listdir(name__startswith='File'))
    resp_inodes = [inode for inode in body['inodes'] if inode['name'].startswith("File")]
    assert len(target_inodes) == len(expected_copied) == len(resp_inodes)

    target_names = sorted(inode['name'] for inode in target_inodes)
    resp_names = sorted(inode['name'] for inode in resp_inodes)
    expected_names = sorted(f"File #{s}" for s in expected_copied)
    assert target_names == expected_names
    assert resp_names == expected_names


def test_update_file_tags(admin_client, ambit, principal_kwargs):
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': ambit.root_folder.id})
    existing_tag = FileTag.objects.create(ambit=ambit, label="Alpha", color='#111111')
    stale_tag = FileTag.objects.create(ambit=ambit, label="Stale", color='#222222')
    AccessControlEntry.objects.all().delete()
    if principal_kwargs:
        if 'user' in principal_kwargs:
            principal_kwargs['privilege'] = Privilege.FULL
        AccessControlEntry.objects.create(inode=ambit.root_folder_id, **principal_kwargs)

    payload = {
        'tags': [
            {'value': existing_tag.id, 'label': "Alpha Renamed", 'color': '#333333'},
            {'label': "New Tag", 'color': '#444444'},
        ],
    }
    response = admin_client.post(f'{admin_url}/update_tags', json.dumps(payload), content_type='application/json')
    if principal_kwargs and not principal_kwargs['privilege'] & Privilege.ADMIN:
        assert response.status_code == 403
        return
    assert response.status_code == 200
    response_tags = response.json()['tags']
    existing_tag.refresh_from_db()
    assert existing_tag.label == "Alpha Renamed"
    assert existing_tag.color == '#333333'
    assert FileTag.objects.filter(id=stale_tag.id).exists() is False
    expected = {
        (existing_tag.id, "Alpha Renamed", '#333333'),
        (FileTag.objects.get(label="New Tag", ambit=ambit).id, "New Tag", '#444444'),
    }
    actual = {(entry['value'], entry['label'], entry['color']) for entry in response_tags}
    assert actual == expected


@pytest.mark.parametrize('access_control', [AccessControl.ALLOW, AccessControl.SOURCE_DENIED])
def test_undo_discarded_inodes(admin_client, admin_user, ambit, uploaded_file, sub_folder, principal_kwargs, access_control):
    """Test restoring deleted inodes from trash folder."""
    trash_folder = FolderModel.objects.get_trash_folder(ambit, admin_user)
    discarded_inodes = FileModel.objects.bulk_create([
        FileModel(
            parent=trash_folder,
            name=f"Discarded #{ordering}",
            file_size=uploaded_file.file_size,
            sha1=uploaded_file.sha1,
            owner=uploaded_file.owner,
            ordering=ordering,
        ) for ordering in range(1, 9)
    ])
    DiscardedInode.objects.bulk_create([
        DiscardedInode(inode=inode.id, previous_parent=sub_folder) for inode in discarded_inodes
    ])
    AccessControlEntry.objects.all().delete()
    if admin_user.is_superuser is False and access_control == AccessControl.ALLOW:
        AccessControlEntry.objects.create(inode=sub_folder.id, **principal_kwargs)

    # verify inodes are not in sub_folder
    assert list(sub_folder.listdir(name__startswith='Discarded')) == []

    # undo deletion
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
    response = admin_client.post(
        f'{admin_url}/undo_discard',
        json.dumps({'inode_ids': [str(inode.id) for inode in discarded_inodes[3:6]]}),
        content_type='application/json',
    )
    if not (admin_user.is_superuser or access_control == AccessControl.ALLOW):
        assert response.status_code == 403
        return

    assert response.status_code == 204

    # Verify inodes are restored to original folder
    restored_inodes = list(sub_folder.listdir(name__startswith="Discarded").order_by('ordering'))
    assert len(restored_inodes) == 3
    restored_ids = {inode['id'] for inode in restored_inodes}
    expected_ids = {inode.id for inode in discarded_inodes[3:6]}
    assert restored_ids == expected_ids

    # Verify inodes are no longer in trash
    remaining_trash = list(trash_folder.listdir(name__startswith="Discarded"))
    assert len(remaining_trash) == 5
    DiscardedInode.objects.filter(inode__in=[inode.id for inode in discarded_inodes[3:6]]).exists() is False


def test_undo_discarded_folder_with_name_conflict(admin_client, admin_user, ambit, uploaded_file, sub_folder):
    """Test restoring inodes when a file with the same name exists in the original folder."""
    trash_folder = FolderModel.objects.get_trash_folder(ambit, admin_user)
    FolderModel.objects.create(
        parent=sub_folder,
        name="Conflicting name",
        owner=admin_user,
    )
    discarded_folder = FolderModel.objects.create(
        parent=trash_folder,
        name="Conflicting name",
        owner=uploaded_file.owner,
    )
    DiscardedInode.objects.create(inode=discarded_folder.id, previous_parent=sub_folder)
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
    response = admin_client.post(
        f'{admin_url}/undo_discard',
        json.dumps({'inode_ids': [str(discarded_folder.id)]}),
        content_type='application/json',
    )
    assert response.status_code == 204
    restored_inodes = list(sub_folder.listdir(name__startswith="Conflicting").order_by('ordering'))
    assert len(restored_inodes) == 2
    assert restored_inodes[0]['name'] == "Conflicting name"
    assert restored_inodes[1]['name'] == "Conflicting name.renamed"


def test_erase_trash_folder(admin_client, admin_user, ambit, sub_folder):
    """Test erasing a trash folder containing a file."""
    trash_folder = FolderModel.objects.get_trash_folder(ambit, admin_user)
    file_name = 'small_file.bin'
    with open(settings.BASE_DIR / 'workdir/assets' / file_name, 'rb') as file_handle:
        discarded_file = SimpleUploadedFile(file_name, file_handle.read(), content_type='application/octet-stream')
    discarded_inode = FileModel.objects.create_from_upload(
        ambit,
        discarded_file,
        folder=trash_folder,
        name="Discarded",
        owner=admin_user,
        ordering=1,
    )
    DiscardedInode.objects.create(inode=discarded_inode.id, previous_parent=sub_folder)
    assert ambit.original_storage.exists(discarded_inode.file_path)

    # Erase the trash folder
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
    erase_response = admin_client.delete(f'{admin_url}/erase_trash_folder')
    assert erase_response.status_code == 200
    response_data = erase_response.json()
    assert 'success_url' in response_data

    # Verify file is deleted physically from disk
    remaining_files = list(trash_folder.listdir(name__startswith="Discarded"))
    assert len(remaining_files) == 0
    assert DiscardedInode.objects.filter(inode=discarded_inode.id).exists() is False
    assert FileModel.objects.filter(id=discarded_inode.id).exists() is False
    assert not ambit.original_storage.exists(discarded_inode.file_path)

#     ambit = sub_folder.get_ambit()
#
#     # Create and delete an inode
#     deletable_file = FileModel.objects.create(
#         parent=sub_folder,
#         name="conflicting_file.txt",
#         file_size=uploaded_file.file_size,
#         sha1=uploaded_file.sha1,
#         owner=admin_user,
#     )
#
#     admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
#     response = admin_client.post(
#         f'{admin_url}/delete',
#         json.dumps({'inode_ids': [str(deletable_file.id)]}),
#         content_type='application/json',
#     )
#     assert response.status_code == 200
#
#     # Create a file with the same name in the original folder
#     FileModel.objects.create(
#         parent=sub_folder,
#         name="conflicting_file.txt",
#         file_size=uploaded_file.file_size,
#         sha1=uploaded_file.sha1,
#         owner=admin_user,
#     )
#
#     # Restore the deleted file
#     trash_folder = ambit.trash_folders.get(owner=admin_user)
#     trash_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
#     restore_response = admin_client.post(
#         f'{trash_url}/undo_discard',
#         json.dumps({'inode_ids': [str(deletable_file.id)]}),
#         content_type='application/json',
#     )
#     assert restore_response.status_code == 204
#
#     # Verify the restored file has a renamed name to avoid conflict
#     restored_inode = sub_folder.listdir(id=str(deletable_file.id)).first()
#     assert restored_inode is not None
#     assert restored_inode['name'] == "conflicting_file.txt.renamed"
#     assert restored_inode['parent'] == str(sub_folder.id)
