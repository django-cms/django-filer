"""
The `structure` endpoint of the file browser, and the session state it reopens on.
"""

import logging
import uuid

import pytest

from finder.browser.urls import reverse_api
from finder.models.folder import FolderModel
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def structure_url(ambit):
    return reverse_api('base-url') + f'structure/{ambit.slug}'


def set_last_folder(client, folder_id):
    session = client.session
    session['finder.last_folder'] = str(folder_id)
    session.save()


class TestLastFolder:
    """
    `finder.last_folder` is a single session key shared by every ambit, and it outlives
    the folder it names. An id which no longer belongs here must not fail the request.
    """

    def test_a_fresh_session_opens_the_root_folder(self, admin_client, structure_url, ambit):
        response = admin_client.get(structure_url)
        assert response.status_code == 200
        assert response.json()['last_folder'] == str(ambit.root_folder_id)

    def test_it_reopens_the_last_folder(self, admin_client, structure_url, sub_folder):
        set_last_folder(admin_client, sub_folder.id)
        assert admin_client.get(structure_url).json()['last_folder'] == str(sub_folder.id)

    def test_a_deleted_folder_falls_back_to_the_root(self, admin_client, structure_url, ambit):
        """What is left behind after `manage.py finder delete-ambit`."""
        set_last_folder(admin_client, uuid.uuid4())
        response = admin_client.get(structure_url)
        assert response.status_code == 200
        assert response.json()['last_folder'] == str(ambit.root_folder_id)

    def test_a_deleted_folder_falls_back_even_with_subfolders(
        self, admin_client, structure_url, ambit, sub_folder,
    ):
        """The old guard only ran when the root folder had subfolders."""
        set_last_folder(admin_client, uuid.uuid4())
        response = admin_client.get(structure_url)
        assert response.status_code == 200
        assert response.json()['last_folder'] == str(ambit.root_folder_id)

    def test_a_folder_of_another_ambit_falls_back_to_the_root(
        self, admin_client, structure_url, ambit, alternative_ambit,
    ):
        """Opening the browser for one ambit must not carry another one's folder over."""
        set_last_folder(admin_client, alternative_ambit.root_folder_id)
        response = admin_client.get(structure_url)
        assert response.status_code == 200
        assert response.json()['last_folder'] == str(ambit.root_folder_id)

    def test_a_malformed_id_falls_back_to_the_root(self, admin_client, structure_url, ambit):
        set_last_folder(admin_client, 'not-a-uuid')
        response = admin_client.get(structure_url)
        assert response.status_code == 200
        assert response.json()['last_folder'] == str(ambit.root_folder_id)

    def test_the_query_parameter_wins_over_the_session(self, admin_client, structure_url, ambit, sub_folder):
        set_last_folder(admin_client, ambit.root_folder_id)
        response = admin_client.get(structure_url, {'folder': str(sub_folder.id)})
        assert response.json()['last_folder'] == str(sub_folder.id)

    def test_a_stale_query_parameter_falls_back_too(self, admin_client, structure_url, ambit):
        response = admin_client.get(structure_url, {'folder': str(uuid.uuid4())})
        assert response.status_code == 200
        assert response.json()['last_folder'] == str(ambit.root_folder_id)

    def test_the_session_is_repaired(self, admin_client, structure_url, ambit):
        """A stale id is replaced, so the next request does not have to fall back again."""
        set_last_folder(admin_client, uuid.uuid4())
        admin_client.get(structure_url)
        assert admin_client.session['finder.last_folder'] == str(ambit.root_folder_id)


class TestUnknownAmbit:
    """
    A slug which does not exist must be refused exactly like one the caller may not read,
    otherwise the endpoint can be used to enumerate the ambits a site has configured.
    """

    def unreadable_ambit_response(self, client, ambit):
        AccessControlEntry.objects.filter(inode=ambit.root_folder_id).delete()
        DefaultAccessControlEntry.objects.filter(folder=ambit.root_folder).delete()
        return client.get(reverse_api('base-url') + f'structure/{ambit.slug}')

    def test_an_unknown_slug_is_refused(self, client, ambit, django_user_model):
        client.force_login(django_user_model.objects.create_user(username='joe'))
        response = client.get(reverse_api('base-url') + 'structure/nosuch')
        assert response.status_code == 403

    def test_it_is_indistinguishable_from_a_missing_permission(self, client, ambit, django_user_model):
        client.force_login(django_user_model.objects.create_user(username='joe'))
        unknown = client.get(reverse_api('base-url') + 'structure/nosuch')
        forbidden = self.unreadable_ambit_response(client, ambit)
        assert unknown.status_code == forbidden.status_code == 403
        assert unknown.content == forbidden.content

    def test_the_response_does_not_echo_the_slug(self, client, django_user_model):
        client.force_login(django_user_model.objects.create_user(username='joe'))
        response = client.get(reverse_api('base-url') + 'structure/secret-ambit')
        assert b'secret-ambit' not in response.content

    def test_the_reason_is_logged_for_the_developer(self, client, caplog, django_user_model):
        client.force_login(django_user_model.objects.create_user(username='joe'))
        with caplog.at_level(logging.WARNING, logger='finder.browser.views'):
            client.get(reverse_api('base-url') + 'structure/nosuch')
        assert 'No ambit named “nosuch”' in caplog.text
        assert 'list-ambits' in caplog.text

    def test_a_superuser_still_gets_the_tree(self, admin_client, ambit):
        assert admin_client.get(reverse_api('base-url') + f'structure/{ambit.slug}').status_code == 200


def test_the_root_folder_still_exists(ambit):
    """Guard against the fallback masking a genuinely broken tree."""
    assert FolderModel.objects.filter(id=ambit.root_folder_id).exists()
