import pytest

from django.db import connection
from django.db.models import Value
from django.test.utils import CaptureQueriesContext

from finder.browser.views import BrowserView
from finder.contrib.image.pil.models import PILImageModel
from finder.lookups import annotate_unified_queryset
from finder.models.file import FileModel
from finder.models.folder import FolderModel
from finder.models.inode import InodeModel


@pytest.mark.parametrize('size', [1, 12])
@pytest.mark.parametrize('view', ['browser', 'admin'])
def test_folder_counts_batched(ambit, size, view):
    folders = FolderModel.objects.bulk_create([
        FolderModel(parent=ambit.root_folder, name=f'folder-{i}') for i in range(size)
    ])
    for folder in folders:
        FolderModel.objects.create(parent=folder, name='nested')
        FileModel.objects.create(parent=folder, name='file', file_name='file.bin', file_size=128)
        PILImageModel.objects.create(parent=folder, name='image', file_name='image.png', file_size=128,
                                     mime_type='image/png', width=10, height=10)

    # Each concrete model needs at most one grouped count, regardless of folder count.
    with CaptureQueriesContext(connection) as queries:
        if view == 'browser':
            entries = BrowserView._get_children(ambit, Value(True), set(), ambit.root_folder)
        else:
            entries = ambit.root_folder.listdir(is_folder=True)
            annotate_unified_queryset(ambit, entries)
            entries = list(entries)

    assert {entry['id'] for entry in entries} == {folder.id for folder in folders}
    assert all(entry['summary'] == '1 Folder, 2 Files' for entry in entries)
    if view == 'browser':
        assert all(entry['has_subfolders'] and entry['children'] is None for entry in entries)
    assert len(queries) <= 1 + len(list(InodeModel.get_models(include_folder=True)))


def test_empty_folder_counts(ambit):
    folder = FolderModel.objects.create(parent=ambit.root_folder, name='empty')
    entries = BrowserView._get_children(ambit, Value(True), {str(folder.id)}, ambit.root_folder)
    assert entries[0]['summary'] == '0 Folders, 0 Files'
    assert entries[0]['has_subfolders'] is False
    assert entries[0]['children'] == []
