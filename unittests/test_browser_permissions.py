"""
Authorization of the browser endpoints.

The endpoints are served by the admin without `admin_view()`, because the
`<finder-file-select>` widget renders on ordinary forms outside the admin. Authorization
is therefore the responsibility of the views, per folder rather than per staff flag.
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
        assert unknown.status_code == 403
        assert unknown.content.decode() == FORBIDDEN


class TestWithReadPermission:
    """Reading must not imply the right to change or destroy."""

    @pytest.fixture
    def reader(self, without_public_access, client, django_user_model):
        user = django_user_model.objects.create_user(username='reader')
        AccessControlEntry.objects.create(
            inode=without_public_access.root_folder_id,
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

    `manage.py finder add-ambit` and `finder.0002_default_ambit` grant READ_WRITE to
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
        client.force_login(django_user_model.objects.create_user(username='joe'))
        assert client.get(f'{base_url}structure/{ambit.slug}').status_code == 200
        assert client.get(f'{base_url}{uploaded_image.id}/fetch').status_code == 200

    def test_the_model_layer_refuses_anonymous(self, ambit):
        from django.contrib.auth.models import AnonymousUser
        from finder.models.permission import Privilege, is_anonymous

        assert is_anonymous(AnonymousUser()) is True
        assert is_anonymous(None) is True
        assert ambit.root_folder.has_permission(AnonymousUser(), Privilege.READ) is False
        assert ambit.root_folder.has_permission(None, Privilege.READ) is False
