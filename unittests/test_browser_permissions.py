"""
Authorization of the browser endpoints.

The endpoints are served by the admin without `admin_view()`, because the
`<finder-file-select>` widget renders on ordinary forms outside the admin. Authorization
is therefore the responsibility of the views, per inode, and — unless FINDER_STAFF_ONLY
is switched off — restricted to staff.
"""

import pytest

from finder.browser.urls import reverse_api
from finder.contrib.image.pil.models import PILImageModel
from finder.models.file import FileModel
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry, Privilege

pytestmark = pytest.mark.django_db

FORBIDDEN = "You do not have permission to browse this folder tree."


@pytest.fixture
def without_public_access(ambit):
    """Drop the “everyone” entries which `manage.py finder add-ambit` creates."""
    AccessControlEntry.objects.filter(user__isnull=True, group__isnull=True).delete()
    DefaultAccessControlEntry.objects.filter(user__isnull=True, group__isnull=True).delete()
    return ambit


@pytest.fixture
def base_url():
    return reverse_api('base-url')


class TestWithoutPermission:
    """An outsider must not be able to read or destroy anything."""

    def test_deleting_a_file_is_refused(self, client, base_url, without_public_access, uploaded_image):
        response = client.delete(f'{base_url}{uploaded_image.id}/change')
        assert response.status_code == 403
        assert response.content.decode() == FORBIDDEN
        assert PILImageModel.objects.filter(id=uploaded_image.id).exists()

    def test_changing_a_file_is_refused(self, client, base_url, without_public_access, uploaded_image):
        response = client.post(f'{base_url}{uploaded_image.id}/change', {'name': 'renamed.png'})
        assert response.status_code == 403
        uploaded_image.refresh_from_db()
        assert uploaded_image.name != 'renamed.png'

    def test_cropping_is_refused(self, client, base_url, without_public_access, uploaded_image):
        response = client.post(f'{base_url}{uploaded_image.id}/crop', {'width': 60, 'height': 60})
        assert response.status_code == 403

    def test_fetching_is_refused(self, client, base_url, without_public_access, uploaded_image):
        response = client.get(f'{base_url}{uploaded_image.id}/fetch')
        assert response.status_code == 403

    def test_an_unknown_inode_is_refused_the_same_way(self, client, base_url, without_public_access,
                                                      missing_inode_id):
        """The response must not reveal whether the inode exists."""
        unknown = client.get(f'{base_url}{missing_inode_id}/fetch')
        assert unknown.status_code == 404
        expected = f"No inode found matching the given lookup: {{'id': UUID('{missing_inode_id}')}}."
        assert unknown.content.decode() == expected


class TestWithReadPermission:
    """Reading must not imply the right to change or destroy."""

    @pytest.fixture
    def reader(self, without_public_access, client, django_user_model):
        user = django_user_model.objects.create_user(username='reader', is_staff=True)
        AccessControlEntry.objects.create(
            inode=without_public_access.root_folder_id,
            user=user,
            privilege=Privilege.READ,
        )
        # files are checked against their own ACL, which they inherit from the default ACL
        DefaultAccessControlEntry.objects.create(
            folder=without_public_access.root_folder,
            user=user,
            privilege=Privilege.READ,
        )
        client.force_login(user)
        return user

    def test_fetching_is_allowed(self, client, base_url, reader, uploaded_image):
        assert client.get(f'{base_url}{uploaded_image.id}/fetch').status_code == 200

    def test_cropping_is_allowed(self, client, base_url, reader, uploaded_image):
        assert client.post(f'{base_url}{uploaded_image.id}/crop', {'width': 60}).status_code == 200

    def test_deleting_is_refused(self, client, base_url, reader, uploaded_image):
        assert client.delete(f'{base_url}{uploaded_image.id}/change').status_code == 403
        assert PILImageModel.objects.filter(id=uploaded_image.id).exists()


class TestWithWritePermission:

    def test_a_superuser_may_delete(self, admin_client, base_url, ambit, uploaded_image):
        assert admin_client.delete(f'{base_url}{uploaded_image.id}/change').status_code == 200
        with pytest.raises(FileModel.DoesNotExist):
            FileModel.objects.get_inode(id=uploaded_image.id)


class TestAnonymousAccess:
    """
    The “everyone” entry means every *signed in* user.

    `manage.py finder add-ambit` and `finder.0001_initial` grant READ_WRITE to
    everyone, so without this rule a fresh installation would publish its folder tree —
    and its delete endpoint — to the internet.
    """

    @pytest.mark.parametrize('action, method, path', [
        ('structure', 'get', 'structure/{slug}'),
        ('list', 'get', '{folder}/list'),
        ('fetch', 'get', '{file}/fetch'),
        ('crop', 'post', '{file}/crop'),
        ('change', 'delete', '{file}/change'),
        ('upload', 'post', '{folder}/upload'),
        ('search', 'get', '{folder}/search?q=png'),
    ])
    def test_every_endpoint_refuses_anonymous(self, client, base_url, ambit, uploaded_image,
                                              action, method, path):
        url = base_url + path.format(
            slug=ambit.slug, folder=ambit.root_folder_id, file=uploaded_image.id,
        )
        response = getattr(client, method)(url)
        assert response.status_code == 403, action
        assert response.content.decode() == FORBIDDEN, action

    def test_nothing_was_destroyed(self, client, base_url, ambit, uploaded_image):
        client.delete(f'{base_url}{uploaded_image.id}/change')
        assert PILImageModel.objects.filter(id=uploaded_image.id).exists()

    def test_a_signed_in_user_is_still_covered_by_everyone(self, client, base_url, ambit,
                                                           uploaded_image, django_user_model):
        """The default ACL keeps working for authenticated users."""
        client.force_login(django_user_model.objects.create_user(username='joe', is_staff=True))
        assert client.get(f'{base_url}structure/{ambit.slug}').status_code == 200
        assert client.get(f'{base_url}{uploaded_image.id}/fetch').status_code == 200

    def test_the_model_layer_refuses_anonymous(self, ambit):
        from django.contrib.auth.models import AnonymousUser
        from finder.models.permission import Privilege, is_anonymous

        assert is_anonymous(AnonymousUser()) is True
        assert is_anonymous(None) is True
        assert ambit.root_folder.has_permission(AnonymousUser(), Privilege.READ) is False
        assert ambit.root_folder.has_permission(None, Privilege.READ) is False


class TestStaffOnly:
    """
    “Everyone” grants READ_WRITE by default, which must not reach the customer or
    subscriber accounts of a site through endpoints that are not behind `admin_view()`.
    """

    @pytest.fixture
    def customer(self, client, django_user_model):
        user = django_user_model.objects.create_user(username='customer')
        client.force_login(user)
        return user

    def test_everyone_does_not_cover_a_user_who_is_not_staff(self, client, base_url, ambit,
                                                             uploaded_image, customer):
        assert client.get(f'{base_url}structure/{ambit.slug}').status_code == 403
        assert client.get(f'{base_url}{uploaded_image.id}/fetch').status_code == 403
        assert client.delete(f'{base_url}{uploaded_image.id}/change').status_code == 403
        assert PILImageModel.objects.filter(id=uploaded_image.id).exists()

    def test_nor_does_an_entry_naming_that_user(self, client, base_url, ambit, uploaded_image, customer):
        AccessControlEntry.objects.create(inode=uploaded_image.id, user=customer, privilege=Privilege.FULL)
        assert uploaded_image.has_permission(customer, Privilege.READ) is False
        assert client.get(f'{base_url}{uploaded_image.id}/fetch').status_code == 403

    def test_it_can_be_switched_off(self, client, base_url, ambit, uploaded_image, customer, settings):
        settings.FINDER_STAFF_ONLY = False
        assert client.get(f'{base_url}{uploaded_image.id}/fetch').status_code == 200


class TestFileLevelAccessControl:
    """A file is checked against its own ACL, not its folder's, as the admin does."""

    @pytest.fixture
    def staff(self, client, without_public_access, django_user_model):
        user = django_user_model.objects.create_user(username='staff', is_staff=True)
        client.force_login(user)
        return user

    def test_write_on_the_folder_does_not_allow_deleting_a_read_only_file(self, client, base_url, staff,
                                                                          uploaded_image):
        AccessControlEntry.objects.create(inode=uploaded_image.folder.id, user=staff, privilege=Privilege.READ_WRITE)
        AccessControlEntry.objects.create(inode=uploaded_image.id, user=staff, privilege=Privilege.READ)
        response = client.delete(f'{base_url}{uploaded_image.id}/change')
        assert response.status_code == 403
        assert PILImageModel.objects.filter(id=uploaded_image.id).exists()

    def test_read_on_the_folder_does_not_allow_cropping_an_unreadable_file(self, client, base_url, staff,
                                                                           uploaded_image):
        AccessControlEntry.objects.create(inode=uploaded_image.folder.id, user=staff, privilege=Privilege.READ)
        assert client.post(f'{base_url}{uploaded_image.id}/crop', {'width': 60}).status_code == 403
        assert client.get(f'{base_url}{uploaded_image.id}/fetch').status_code == 403


class TestSearch:

    @pytest.fixture
    def staff(self, client, without_public_access, django_user_model):
        user = django_user_model.objects.create_user(username='staff', is_staff=True)
        client.force_login(user)
        return user

    @pytest.fixture
    def sub_folder_readable(self, staff, sub_folder):
        AccessControlEntry.objects.create(inode=sub_folder.id, user=staff, privilege=Privilege.READ)
        return sub_folder

    def test_searching_an_unreadable_folder_is_refused(self, client, base_url, staff, ambit, uploaded_image):
        response = client.get(f'{base_url}{ambit.root_folder_id}/search?q=png')
        assert response.status_code == 403
        assert response.content.decode() == FORBIDDEN

    def test_the_search_zone_cookie_does_not_escalate_to_the_root(self, client, base_url, sub_folder_readable,
                                                                  uploaded_image):
        client.cookies['django-finder-search-zone'] = 'everywhere'
        response = client.get(f'{base_url}{sub_folder_readable.id}/search?q=png')
        assert response.status_code == 403

    def test_files_the_user_may_not_read_are_left_out(self, client, base_url, staff, ambit, uploaded_image):
        AccessControlEntry.objects.create(inode=ambit.root_folder_id, user=staff, privilege=Privilege.READ)
        name = uploaded_image.name.rsplit('.', 1)[0]
        response = client.get(f'{base_url}{ambit.root_folder_id}/search?q={name}')
        assert response.status_code == 200
        assert response.json()['files'] == []

        AccessControlEntry.objects.create(inode=uploaded_image.id, user=staff, privilege=Privilege.READ)
        response = client.get(f'{base_url}{ambit.root_folder_id}/search?q={name}')
        assert [entry['id'] for entry in response.json()['files']] == [str(uploaded_image.id)]


def test_unexpected_errors_are_not_echoed(admin_client, base_url, ambit, monkeypatch):
    from finder.browser.views import BrowserView

    def fail(*args, **kwargs):
        raise RuntimeError("secret storage path /var/media/xyz")

    monkeypatch.setattr(BrowserView, 'structure', fail)
    response = admin_client.get(f'{base_url}structure/{ambit.slug}')
    assert response.status_code == 400
    assert 'secret' not in response.content.decode()
