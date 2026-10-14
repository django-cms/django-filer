from unittest.mock import patch

import pytest

from django.db.models.query import QuerySet

from finder.contrib.image.pil.models import PILImageModel
from finder.models.file import FileModel
from finder.models.folder import FolderModel


@pytest.mark.parametrize('size', [0, 40])
def test_max_ordering_scalar(ambit, size):
    folder = ambit.root_folder
    FileModel.objects.bulk_create([
        FileModel(parent=folder, name=f'file-{i}', file_name=f'{i}.bin', file_size=1, ordering=i)
        for i in range(size)
    ])
    if size:
        FolderModel.objects.create(parent=folder, name='nested', ordering=100)
        PILImageModel.objects.create(parent=folder, name='image', file_name='image.png', file_size=1,
                                     mime_type='image/png', width=10, height=10, ordering=200)
    loaded = 0
    fetch_all = QuerySet._fetch_all

    def count_rows(queryset):
        nonlocal loaded
        uncached = queryset._result_cache is None
        fetch_all(queryset)
        if uncached:
            loaded += len(queryset._result_cache)

    # Aggregate SQL must not transfer every ordering value to Python.
    with patch.object(QuerySet, '_fetch_all', count_rows):
        result = folder.get_max_ordering()

    assert result == (200 if size else 0)
    assert loaded <= 1
