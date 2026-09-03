import json
import pytest
import zipfile

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from finder.contrib.archive.models import ArchiveModel
from finder.models.file import FileModel
from finder.models.folder import FolderModel


@pytest.fixture
def archive_url(ambit):
    """Endpoint to create a ZIP archive from the selected inodes of a folder."""
    base_url = reverse('admin:finder_foldermodel_changelist')

    def build(folder):
        return f'{base_url}{folder.id}/archive'

    return build


@pytest.fixture
def unarchive_url(ambit):
    """Endpoint to extract a ZIP archive into the folder it is stored in."""
    base_url = reverse('admin:finder_filemodel_changelist')

    def build(file_obj):
        return f'{base_url}{file_obj.id}/unarchive'

    return build


@pytest.fixture
def zip_payload():
    def build(members):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zip_ref:
            for name, content in members.items():
                if content is None:
                    zip_ref.mkdir(name)
                else:
                    zip_ref.writestr(name, content)
        return buffer.getvalue()

    return build


@pytest.fixture
def upload_archive(ambit, admin_user, zip_payload):
    def build(name='archive.zip', members=None, payload=None):
        if payload is None:
            payload = zip_payload(members or {'plain.txt': b"content"})
        uploaded_file = SimpleUploadedFile(name, payload, content_type='application/zip')
        return ArchiveModel.objects.create_from_upload(
            ambit,
            uploaded_file,
            folder=ambit.root_folder,
            owner=admin_user,
        )

    return build


@pytest.fixture
def make_file(ambit, admin_user):
    def build(name, folder=None, content=b"payload"):
        uploaded_file = SimpleUploadedFile(name, content, content_type='application/octet-stream')
        return FileModel.objects.create_from_upload(
            ambit,
            uploaded_file,
            folder=folder or ambit.root_folder,
            owner=admin_user,
        )

    return build


def test_archive_selected_files(admin_client, ambit, archive_url, make_file):
    first = make_file('first.bin', content=b"first")
    second = make_file('second.bin', content=b"second")
    response = admin_client.post(
        archive_url(ambit.root_folder),
        data=json.dumps({'archive_name': "my-archive", 'inode_ids': [str(first.id), str(second.id)]}),
        content_type='application/json',
    )
    assert response.status_code == 200
    new_file = response.json()['new_file']
    assert new_file['name'] == "my-archive"
    assert new_file['is_folder'] is False

    archive_obj = ArchiveModel.objects.get(name="my-archive")
    assert archive_obj.file_name == 'my-archive.zip'
    assert archive_obj.mime_type == 'application/zip'
    assert archive_obj.file_size > 0
    assert len(archive_obj.sha1) == 40
    assert archive_obj.parent == ambit.root_folder

    with ambit.original_storage.open(archive_obj.file_path) as handle:
        with zipfile.ZipFile(handle) as zip_ref:
            assert sorted(zip_ref.namelist()) == ['first.bin', 'second.bin']
            assert zip_ref.read('first.bin') == b"first"


def test_archive_selected_folder(admin_client, ambit, sub_folder, archive_url, make_file):
    make_file('nested.bin', folder=sub_folder, content=b"nested")
    response = admin_client.post(
        archive_url(ambit.root_folder),
        data=json.dumps({'archive_name': "with-folder", 'inode_ids': [str(sub_folder.id)]}),
        content_type='application/json',
    )
    assert response.status_code == 200

    archive_obj = ArchiveModel.objects.get(name="with-folder")
    with ambit.original_storage.open(archive_obj.file_path) as handle:
        with zipfile.ZipFile(handle) as zip_ref:
            assert sorted(zip_ref.namelist()) == ['Sub Folder/', 'Sub Folder/nested.bin']


def test_archive_name_keeps_zip_suffix(admin_client, ambit, archive_url, make_file):
    file_obj = make_file('first.bin')
    admin_client.post(
        archive_url(ambit.root_folder),
        data=json.dumps({'archive_name': "already.zip", 'inode_ids': [str(file_obj.id)]}),
        content_type='application/json',
    )
    assert ArchiveModel.objects.get(name="already.zip").file_name == 'already.zip'


def test_archive_rejects_get_request(admin_client, ambit, archive_url):
    response = admin_client.get(archive_url(ambit.root_folder))
    assert response.status_code == 400
    assert response.text == "Method GET not allowed. Only POST requests are allowed."


@pytest.mark.parametrize('body', [
    {'archive_name': "", 'inode_ids': ['00000000-0000-0000-0000-000000000000']},
    {'archive_name': "my-archive", 'inode_ids': []},
    {},
])
def test_archive_with_incomplete_body(admin_client, ambit, archive_url, body):
    response = admin_client.post(
        archive_url(ambit.root_folder),
        data=json.dumps(body),
        content_type='application/json',
    )
    assert response.status_code == 400
    assert response.text == "Archive name and inode IDs are required"


def test_archive_with_unknown_inode(admin_client, ambit, missing_inode_id, archive_url):
    response = admin_client.post(
        archive_url(ambit.root_folder),
        data=json.dumps({'archive_name': "my-archive", 'inode_ids': [str(missing_inode_id)]}),
        content_type='application/json',
    )
    assert response.status_code == 400
    assert response.text == f"Inode with ID “{missing_inode_id}” not found"
    assert ArchiveModel.objects.filter(name="my-archive").exists() is False


@pytest.mark.django_db(transaction=True)
def test_unarchive_file(admin_client, ambit, upload_archive, unarchive_url):
    archive_obj = upload_archive(members={
        'readme.txt': b"read me",
        'sub/': None,
        'sub/nested.txt': b"nested",
    })
    response = admin_client.post(unarchive_url(archive_obj))
    assert response.status_code == 200
    assert response.text == 'Successfully extracted ZIP archive “archive.zip” to folder “archive”.'

    folder_obj = FolderModel.objects.get(name='archive', parent=ambit.root_folder)
    sub_folder_obj = FolderModel.objects.get(name='sub', parent=folder_obj)
    readme = FileModel.objects.get(name='readme.txt', parent=folder_obj)
    nested = FileModel.objects.get(name='nested.txt', parent=sub_folder_obj)
    assert readme.mime_type == 'text/plain'
    assert readme.file_size == len(b"read me")

    # the payload is copied into the storage once the transaction has been committed
    with ambit.original_storage.open(nested.file_path) as handle:
        assert handle.read() == b"nested"


@pytest.mark.django_db(transaction=True)
def test_unarchive_file_without_suffix(admin_client, ambit, upload_archive, unarchive_url):
    """An archive whose name carries no known suffix is extracted into a folder of the very same name."""
    archive_obj = upload_archive(name='bundle')
    response = admin_client.post(unarchive_url(archive_obj))
    assert response.status_code == 200
    assert FolderModel.objects.filter(name='bundle', parent=ambit.root_folder).exists() is True


def test_unarchive_rejects_get_request(admin_client, ambit, upload_archive, unarchive_url):
    archive_obj = upload_archive()
    response = admin_client.get(unarchive_url(archive_obj))
    assert response.status_code == 400
    assert response.text == "Method GET not allowed. Only POST requests are allowed."


def test_unarchive_into_existing_folder(admin_client, ambit, admin_user, upload_archive, unarchive_url):
    archive_obj = upload_archive()
    FolderModel.objects.create(parent=ambit.root_folder, name='archive', owner=admin_user)
    response = admin_client.post(unarchive_url(archive_obj))
    assert response.status_code == 409
    assert response.text == "Cannot extract archive. A folder named “archive” already exists."


def test_unarchive_reports_extraction_errors(admin_client, ambit, upload_archive, unarchive_url, monkeypatch):
    """Anything going wrong while extracting is reported as “unsupported media type”."""
    archive_obj = upload_archive(members={'readme.txt': b"read me"})

    def boom(**kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(FolderModel.objects, 'create', boom)
    response = admin_client.post(unarchive_url(archive_obj))
    assert response.status_code == 415
    assert "disk on fire" in response.text


def test_archive_menu_extension_is_registered(admin_client, ambit, root_folder_url):
    """The ZIP menu extension is announced to the folder admin view."""
    response = admin_client.get(root_folder_url)
    assert response.status_code == 200
    assert '"menu_extensions": [{"component": "Archive"}]' in response.text


def test_archive_editor_settings(admin_client, ambit, upload_archive):
    from django.contrib import admin as django_admin

    archive_obj = upload_archive()
    model_admin = django_admin.site._registry[ArchiveModel]
    response = admin_client.get(model_admin.get_inode_url(ambit.slug, str(archive_obj.id)))
    assert response.status_code == 200
    assert '"download_file": true' in response.text
    assert '"editor_component": "Archive"' in response.text
