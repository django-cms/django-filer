import pytest

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from finder.contrib.common.models import CodeFileModel, PDFFileModel, SpreadsheetModel
from finder.models.file import FileModel
from finder.models.folder import FolderModel
from finder.models.filetag import FileTag
from finder.models.permission import AccessControlEntry, Privilege


@pytest.fixture(autouse=True)
def setup(ambit, admin_user, staff_users):
    file_name = 'small_file.bin'
    with open(settings.BASE_DIR / 'workdir/assets' / file_name, 'rb') as file_handle:
        uploaded_file = SimpleUploadedFile(file_name, file_handle.read(), content_type='application/octet-stream')
    red_tag, green_tag, yellow_tag, cyan_tag, blue_tag, magenta_tag = FileTag.objects.bulk_create([
        FileTag(label='red', ambit=ambit, color='FF0000'),
        FileTag(label='green', ambit=ambit, color='00FF00'),
        FileTag(label='yellow', ambit=ambit, color='FFFF00'),
        FileTag(label='cyan', ambit=ambit, color='00FFFF'),
        FileTag(label='blue', ambit=ambit, color='0000FF'),
        FileTag(label='magenta', ambit=ambit, color='FF00FF'),
    ])
    file_obj = FileModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=ambit.root_folder,
        owner=admin_user,
    )
    file_obj.tags.add(red_tag, green_tag, blue_tag)
    code_file = CodeFileModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=ambit.root_folder,
        owner=staff_users[0],  # alice
        mime_type='text/x-python',
    )
    code_file.tags.add(red_tag, yellow_tag)
    uploaded_file.content_type = 'application/vnd.oasis.opendocument.spreadsheet'
    spreadsheet_file = SpreadsheetModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        folder=ambit.root_folder,
        owner=staff_users[2],  # charlie
    )
    spreadsheet_file.tags.add(magenta_tag)
    sub_folder = FolderModel.objects.create(
        parent=ambit.root_folder,
        name="Sub Folder",
        owner=admin_user,
    )
    AccessControlEntry.objects.create(inode=sub_folder.id, user=staff_users[1], privilege=Privilege.READ_WRITE)
    pdf_file = PDFFileModel.objects.create_from_upload(
        ambit,
        uploaded_file,
        name='sample.pdf',
        folder=sub_folder,
        owner=staff_users[1],  # bob
        mime_type='application/pdf',
    )
    pdf_file.tags.add(green_tag, cyan_tag)


def test_unified_query(ambit):
    red_tag, green_tag, blue_tag, magenta_tag = (
        FileTag.objects.get(label='red'),
        FileTag.objects.get(label='green'),
        FileTag.objects.get(label='blue'),
        FileTag.objects.get(label='magenta'),
    )
    assert len(ambit.root_folder.listdir()) == 4
    assert len(ambit.root_folder.listdir(is_folder=True)) == 1
    assert len(ambit.root_folder.listdir(is_folder=False)) == 3
    assert len(ambit.root_folder.listdir(mime_types=['*/*'])) == 4
    assert len(ambit.root_folder.listdir(mime_types=['application/*'])) == 2
    assert len(ambit.root_folder.listdir(mime_types=['inode/directory'])) == 1
    assert len(ambit.root_folder.listdir(mime_types=['application/vnd.oasis.opendocument.spreadsheet'])) == 1
    assert len(ambit.root_folder.listdir(mime_types=['application/pdf'])) == 0
    assert len(ambit.root_folder.listdir(mime_types=['application/vnd.oasis.opendocument.spreadsheet', 'text/x-python'])) == 2
    assert len(ambit.root_folder.listdir(tags__in=[red_tag])) == 3  # folders have no tags
    assert len(ambit.root_folder.listdir(tags__in=[red_tag], is_folder=False)) == 2
    assert len(ambit.root_folder.listdir(tags__in=[green_tag, blue_tag, magenta_tag], is_folder=False)) == 2


def test_get_inode(ambit):
    FileModel.objects.get_inode(name='sample.pdf')
    pdf_file = FileModel.objects.get_inode(name='sample.pdf', is_folder=False)
    assert isinstance(pdf_file, PDFFileModel)
    assert pdf_file.pretty_path == "Root / Sub Folder / sample.pdf"
    sub_folder_id = ambit.root_folder.listdir(is_folder=True)[0]['id']
    assert len(FolderModel.objects.get_inode(id=sub_folder_id).listdir()) == 1
