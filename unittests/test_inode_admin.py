import json
import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from finder.models.folder import FolderModel
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry, Privilege


@pytest.fixture
def principals_url():
    return reverse('admin:finder_foldermodel_changelist') + 'principals'


@pytest.fixture
def permissions_url(ambit):
    base_url = reverse('admin:finder_foldermodel_changelist')
    def _url(inode_id, **params):
        url = f'{base_url}{inode_id}/permissions'
        if params:
            query = '&'.join(f'{k}' for k in params)
            url = f'{url}?{query}'
        return url
    return _url


@pytest.fixture
def staff_users():
    User = get_user_model()
    users = User.objects.bulk_create([
        User(username='alice', is_staff=True),
        User(username='bob', is_staff=True),
        User(username='charlie', is_staff=True),
    ])
    return users


@pytest.fixture
def groups():
    return Group.objects.bulk_create([
        Group(name='Editors'),
        Group(name='Reviewers'),
        Group(name='Designers'),
    ])


def test_lookup_principals_without_query(admin_client, admin_user, principals_url, staff_users, groups):
    """Test that lookup_principals returns all users and groups when no search query is given."""
    response = admin_client.get(principals_url)
    assert response.status_code == 200
    results = response.json()['access_control_results']

    # First entry should always be "Everyone"
    assert results[0]['type'] == 'everyone'
    assert results[0]['principal'] is None
    assert results[0]['is_current_user'] is False

    # All staff users plus admin_user should be returned
    user_entries = [r for r in results if r['type'] == 'user']
    user_names = {r['name'] for r in user_entries}
    assert {'alice', 'bob', 'charlie', admin_user.username}.issubset(user_names)

    # The admin_user entry should have is_current_user=True
    admin_entry = next(r for r in user_entries if r['principal'] == admin_user.id)
    assert admin_entry['is_current_user'] is True

    # All groups should be returned
    group_entries = [r for r in results if r['type'] == 'group']
    group_names = {r['name'] for r in group_entries}
    assert {'Editors', 'Reviewers', 'Designers'}.issubset(group_names)


def test_lookup_principals_with_query(admin_client, principals_url, staff_users, groups):
    """Test that lookup_principals filters users and groups by the search query."""
    response = admin_client.get(f'{principals_url}?q=ali')
    assert response.status_code == 200
    results = response.json()['access_control_results']

    # "Everyone" is always included
    assert results[0]['type'] == 'everyone'

    # Only 'alice' should match among users
    user_entries = [r for r in results if r['type'] == 'user']
    assert len(user_entries) == 1
    assert user_entries[0]['name'] == 'alice'

    # No groups should match 'ali'
    group_entries = [r for r in results if r['type'] == 'group']
    assert len(group_entries) == 0


def test_lookup_principals_filters_groups(admin_client, principals_url, staff_users, groups):
    """Test that lookup_principals filters groups by name."""
    response = admin_client.get(f'{principals_url}?q=edit')
    assert response.status_code == 200
    results = response.json()['access_control_results']

    user_entries = [r for r in results if r['type'] == 'user']
    assert len(user_entries) == 0

    group_entries = [r for r in results if r['type'] == 'group']
    assert len(group_entries) == 1
    assert group_entries[0]['name'] == 'Editors'


def test_lookup_principals_no_match(admin_client, principals_url, staff_users, groups):
    """Test that lookup_principals returns only 'Everyone' when no users or groups match."""
    response = admin_client.get(f'{principals_url}?q=nonexistent')
    assert response.status_code == 200
    results = response.json()['access_control_results']

    assert len(results) == 1
    assert results[0]['type'] == 'everyone'


def test_lookup_principals_wrong_method(admin_client, principals_url):
    """Test that lookup_principals rejects non-GET requests."""
    response = admin_client.post(principals_url, content_type='application/json')
    assert response.status_code == 405


def test_get_permissions_empty(admin_client, ambit, uploaded_file, permissions_url):
    """Test GET permissions on an inode with no ACL entries returns an empty list."""
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    response = admin_client.get(permissions_url(uploaded_file.id))
    assert response.status_code == 200
    acl = response.json()['access_control_list']
    assert acl == []


def test_get_permissions_with_entries(admin_client, admin_user, ambit, uploaded_file, permissions_url, staff_users, groups):
    """Test GET permissions returns existing ACL entries with correct structure."""
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    alice = staff_users[0]
    editors = groups[0]
    AccessControlEntry.objects.bulk_create([
        AccessControlEntry(inode=uploaded_file.id, user=admin_user, privilege=Privilege.FULL),
        AccessControlEntry(inode=uploaded_file.id, user=alice, privilege=Privilege.READ),
        AccessControlEntry(inode=uploaded_file.id, group=editors, privilege=Privilege.READ_WRITE),
        AccessControlEntry(inode=uploaded_file.id, privilege=Privilege.READ),  # everyone
    ])

    response = admin_client.get(permissions_url(uploaded_file.id))
    assert response.status_code == 200
    acl = response.json()['access_control_list']
    assert len(acl) == 4

    acl_by_type = {}
    for entry in acl:
        key = (entry['type'], entry.get('principal'))
        acl_by_type[key] = entry

    # admin_user entry
    admin_entry = acl_by_type[('user', admin_user.id)]
    assert admin_entry['privilege'] == Privilege.FULL
    assert admin_entry['is_current_user'] is True

    # alice entry
    alice_entry = acl_by_type[('user', alice.id)]
    assert alice_entry['privilege'] == Privilege.READ
    assert alice_entry['is_current_user'] is False

    # group entry
    group_entry = acl_by_type[('group', editors.id)]
    assert group_entry['privilege'] == Privilege.READ_WRITE
    assert group_entry['is_current_user'] is False

    # everyone entry
    everyone_entry = acl_by_type[('everyone', None)]
    assert everyone_entry['privilege'] == Privilege.READ
    assert everyone_entry['is_current_user'] is False


def test_get_default_permissions(admin_client, admin_user, ambit, permissions_url, groups):
    """Test GET with ?default returns default ACL entries for a folder."""
    sub_folder = FolderModel.objects.create(
        parent=ambit.root_folder,
        name='ACL Test Folder',
        owner=admin_user,
    )
    editors = groups[0]
    DefaultAccessControlEntry.objects.create(folder=sub_folder, group=editors, privilege=Privilege.READ_WRITE)
    DefaultAccessControlEntry.objects.create(folder=sub_folder, privilege=Privilege.READ)  # everyone

    response = admin_client.get(permissions_url(sub_folder.id, default=''))
    assert response.status_code == 200
    acl = response.json()['access_control_list']
    assert len(acl) == 2

    types = {entry['type'] for entry in acl}
    assert types == {'group', 'everyone'}


def test_set_permissions(admin_client, admin_user, ambit, uploaded_file, permissions_url, staff_users):
    """Test POST to set new ACL entries on an inode."""
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    # superuser needs ADMIN privilege to set permissions
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=admin_user, privilege=Privilege.FULL)
    alice = staff_users[0]

    new_acl = [
        {'type': 'user', 'principal': admin_user.id, 'privilege': Privilege.FULL},
        {'type': 'user', 'principal': alice.id, 'privilege': Privilege.READ_WRITE},
        {'type': 'everyone', 'principal': None, 'privilege': Privilege.READ},
    ]
    response = admin_client.post(
        permissions_url(uploaded_file.id),
        json.dumps({'access_control_list': new_acl}),
        content_type='application/json',
    )
    assert response.status_code == 200
    acl = response.json()['access_control_list']
    assert len(acl) == 3

    # Verify entries were persisted
    assert AccessControlEntry.objects.filter(inode=uploaded_file.id).count() == 3
    assert AccessControlEntry.objects.filter(inode=uploaded_file.id, user=alice, privilege=Privilege.READ_WRITE).exists()
    assert AccessControlEntry.objects.filter(inode=uploaded_file.id, user__isnull=True, group__isnull=True, privilege=Privilege.READ).exists()


def test_update_permissions(admin_client, admin_user, ambit, uploaded_file, permissions_url, staff_users):
    """Test POST to update an existing ACL entry's privilege."""
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    alice = staff_users[0]
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=admin_user, privilege=Privilege.FULL)
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=alice, privilege=Privilege.READ)

    # Update alice's privilege from READ to READ_WRITE
    updated_acl = [
        {'type': 'user', 'principal': admin_user.id, 'privilege': Privilege.FULL},
        {'type': 'user', 'principal': alice.id, 'privilege': Privilege.READ_WRITE},
    ]
    response = admin_client.post(
        permissions_url(uploaded_file.id),
        json.dumps({'access_control_list': updated_acl}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert AccessControlEntry.objects.get(inode=uploaded_file.id, user=alice).privilege == Privilege.READ_WRITE


def test_remove_permissions(admin_client, admin_user, ambit, uploaded_file, permissions_url, staff_users):
    """Test POST with a reduced ACL removes entries not in the new list."""
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    alice = staff_users[0]
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=admin_user, privilege=Privilege.FULL)
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=alice, privilege=Privilege.READ)
    AccessControlEntry.objects.create(inode=uploaded_file.id, privilege=Privilege.READ)  # everyone

    # Post only admin_user entry — alice and everyone should be removed
    reduced_acl = [
        {'type': 'user', 'principal': admin_user.id, 'privilege': Privilege.FULL},
    ]
    response = admin_client.post(
        permissions_url(uploaded_file.id),
        json.dumps({'access_control_list': reduced_acl}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert AccessControlEntry.objects.filter(inode=uploaded_file.id).count() == 1
    assert AccessControlEntry.objects.filter(inode=uploaded_file.id, user=alice).exists() is False
    assert AccessControlEntry.objects.filter(inode=uploaded_file.id, user__isnull=True, group__isnull=True).exists() is False


def test_set_default_permissions(admin_client, admin_user, ambit, permissions_url, groups):
    """Test POST with to_default=True sets default ACL on a folder."""
    sub_folder = FolderModel.objects.create(
        parent=ambit.root_folder,
        name='Default ACL Folder',
        owner=admin_user,
    )
    AccessControlEntry.objects.create(inode=sub_folder.id, user=admin_user, privilege=Privilege.FULL)
    editors = groups[0]

    new_default_acl = [
        {'type': 'group', 'principal': editors.id, 'privilege': Privilege.READ_WRITE},
        {'type': 'everyone', 'principal': None, 'privilege': Privilege.READ},
    ]
    response = admin_client.post(
        permissions_url(sub_folder.id),
        json.dumps({'access_control_list': new_default_acl, 'to_default': True}),
        content_type='application/json',
    )
    assert response.status_code == 200
    acl = response.json()['access_control_list']
    assert len(acl) == 2

    assert DefaultAccessControlEntry.objects.filter(folder=sub_folder).count() == 2
    assert DefaultAccessControlEntry.objects.filter(folder=sub_folder, group=editors, privilege=Privilege.READ_WRITE).exists()


def test_set_permissions_denied(admin_client, admin_user, ambit, uploaded_file, permissions_url, staff_users):
    """Test POST to set permissions fails when user lacks ADMIN privilege."""
    admin_user.is_superuser = False
    admin_user.save(update_fields=['is_superuser'])
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    # Only give the user READ_WRITE, not ADMIN
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=admin_user, privilege=Privilege.READ_WRITE)

    new_acl = [
        {'type': 'everyone', 'principal': None, 'privilege': Privilege.READ},
    ]
    response = admin_client.post(
        permissions_url(uploaded_file.id),
        json.dumps({'access_control_list': new_acl}),
        content_type='application/json',
    )
    assert response.status_code == 403


def test_dispatch_permissions_not_found(admin_client, permissions_url, missing_inode_id):
    """Test dispatch_permissions returns 404 for a non-existent inode."""
    response = admin_client.get(permissions_url(missing_inode_id))
    assert response.status_code == 404


def test_dispatch_permissions_wrong_method(admin_client, ambit, uploaded_file, permissions_url):
    """Test dispatch_permissions rejects unsupported HTTP methods."""
    response = admin_client.delete(permissions_url(uploaded_file.id))
    assert response.status_code == 405


def test_dispatch_permissions_invalid_payload(admin_client, admin_user, ambit, uploaded_file, permissions_url):
    """Test POST with invalid JSON returns 400."""
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=admin_user, privilege=Privilege.FULL)

    response = admin_client.post(
        permissions_url(uploaded_file.id),
        'not valid json',
        content_type='application/json',
    )
    assert response.status_code == 400


def test_dispatch_permissions_missing_key(admin_client, admin_user, ambit, uploaded_file, permissions_url):
    """Test POST with missing 'access_control_list' key returns 400."""
    AccessControlEntry.objects.filter(inode=uploaded_file.id).delete()
    AccessControlEntry.objects.create(inode=uploaded_file.id, user=admin_user, privilege=Privilege.FULL)

    response = admin_client.post(
        permissions_url(uploaded_file.id),
        json.dumps({'wrong_key': []}),
        content_type='application/json',
    )
    assert response.status_code == 400


@pytest.fixture
def toggle_pin_url(ambit):
    base_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': ambit.root_folder.id})
    return f'{base_url}/toggle_pin'


@pytest.fixture
def sub_folders(ambit, admin_user):
    return [
        FolderModel.objects.create(parent=ambit.root_folder, name=f'Folder {i}', owner=admin_user)
        for i in range(1, 4)
    ]


def test_toggle_pin_folder(admin_client, admin_user, ambit, toggle_pin_url, sub_folders):
    """Test pinning a folder creates a PinnedFolder entry and returns it in favorite_folders."""
    from finder.models.folder import PinnedFolder

    folder_to_pin = sub_folders[0]
    response = admin_client.post(
        toggle_pin_url,
        json.dumps({'pinned_id': str(folder_to_pin.id)}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert PinnedFolder.objects.filter(owner=admin_user, folder=folder_to_pin).exists()

    favorite_folders = response.json()['favorite_folders']
    pinned_entry = next(f for f in favorite_folders if f.get('id') == str(folder_to_pin.id) and f.get('is_pinned'))
    assert pinned_entry['name'] == 'Folder 1'


def test_toggle_unpin_folder(admin_client, admin_user, ambit, toggle_pin_url, sub_folders):
    """Test toggling a pinned folder again unpins it (deletes the PinnedFolder entry)."""
    from finder.models.folder import PinnedFolder

    folder_to_pin = sub_folders[0]
    PinnedFolder.objects.create(ambit=ambit, owner=admin_user, folder=folder_to_pin)
    assert PinnedFolder.objects.filter(owner=admin_user, folder=folder_to_pin).exists()

    # Toggle again to unpin
    response = admin_client.post(
        toggle_pin_url,
        json.dumps({'pinned_id': str(folder_to_pin.id)}),
        content_type='application/json',
    )
    assert response.status_code == 200
    assert PinnedFolder.objects.filter(owner=admin_user, folder=folder_to_pin).exists() is False

    favorite_folders = response.json()['favorite_folders']
    pinned_ids = [f['id'] for f in favorite_folders if f.get('is_pinned')]
    assert str(folder_to_pin.id) not in pinned_ids


def test_toggle_unpin_current_folder(admin_client, admin_user, ambit, sub_folders):
    """Test unpinning the current folder returns a success_url redirecting to the parent."""
    from finder.models.folder import PinnedFolder

    current_folder = sub_folders[0]
    PinnedFolder.objects.create(ambit=ambit, owner=admin_user, folder=current_folder)

    # Use current_folder as the folder_id in the URL
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': current_folder.id})
    response = admin_client.post(
        f'{admin_url}/toggle_pin',
        json.dumps({'pinned_id': str(current_folder.id)}),
        content_type='application/json',
    )
    assert response.status_code == 200
    body = response.json()
    assert 'success_url' in body
    assert str(ambit.root_folder.id) in body['success_url']
    assert PinnedFolder.objects.filter(owner=admin_user, folder=current_folder).exists() is False


def test_toggle_pin_multiple_folders(admin_client, admin_user, ambit, toggle_pin_url, sub_folders):
    """Test pinning multiple folders shows all of them in favorite_folders."""
    from finder.models.folder import PinnedFolder

    for folder in sub_folders[:2]:
        response = admin_client.post(
            toggle_pin_url,
            json.dumps({'pinned_id': str(folder.id)}),
            content_type='application/json',
        )
        assert response.status_code == 200

    assert PinnedFolder.objects.filter(owner=admin_user).count() == 2
    favorite_folders = response.json()['favorite_folders']
    pinned_entries = [f for f in favorite_folders if f.get('is_pinned')]
    pinned_names = {f['name'] for f in pinned_entries}
    assert {'Folder 1', 'Folder 2'}.issubset(pinned_names)


def test_toggle_pin_missing_pinned_id(admin_client, toggle_pin_url):
    """Test toggle_pin returns 400 when pinned_id is missing from the body."""
    response = admin_client.post(
        toggle_pin_url,
        json.dumps({}),
        content_type='application/json',
    )
    assert response.status_code == 400


def test_toggle_pin_wrong_method(admin_client, toggle_pin_url, sub_folders):
    """Test toggle_pin rejects non-POST requests."""
    response = admin_client.get(toggle_pin_url)
    assert response.status_code == 405


def test_toggle_pin_wrong_content_type(admin_client, toggle_pin_url, sub_folders):
    """Test toggle_pin rejects non-JSON content type."""
    response = admin_client.post(toggle_pin_url, content_type='text/plain')
    assert response.status_code == 415


def test_toggle_pin_missing_folder(admin_client, missing_inode_id):
    """Test toggle_pin returns 404 when the folder_id in the URL does not exist."""
    admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': missing_inode_id})
    response = admin_client.post(
        f'{admin_url}/toggle_pin',
        json.dumps({'pinned_id': str(missing_inode_id)}),
        content_type='application/json',
    )
    assert response.status_code == 404

