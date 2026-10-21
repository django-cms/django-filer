from unittest.mock import patch

import pytest

from django.urls import reverse

from finder.browser.views import BrowserView
from finder.models.file import FileModel
from finder.models.inode import InodeManager


@pytest.mark.parametrize('action', ['list', 'search'])
@pytest.mark.parametrize('offset', [0, 3, 8])
def test_serialize_only_page(admin_client, ambit, monkeypatch, action, offset):
    FileModel.objects.bulk_create([
        FileModel(parent=ambit.root_folder, name=f'file-{i}', file_name=f'{i}.bin', file_size=128, ordering=i)
        for i in range(8)
    ])
    url = reverse('finder-api:base-url') + f'{ambit.root_folder_id}/{action}'
    admin_client.cookies['django-finder-sorting'] = 'name_desc'
    complete = admin_client.get(url, {'q': 'file'}).json()['files']
    monkeypatch.setattr(BrowserView, 'limit', 3)

    # Count serialization work, independently of database speed and query plans.
    with patch.object(InodeManager, 'get_proxy_object', wraps=InodeManager.get_proxy_object) as serialize:
        response = admin_client.get(url, {'q': 'file', 'offset': offset})

    assert response.status_code == 200
    payload = response.json()
    assert payload['files'] == complete[offset:offset + 3]
    assert payload['offset'] == (offset + 3 if offset + 3 < len(complete) else None)
    assert serialize.call_count == len(payload['files'])
