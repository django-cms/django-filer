"""
The browser API is served by the admin, but without the admin's permission gate.
"""

import pytest

from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_the_admin_serves_the_api(ambit):
    assert reverse('admin:finder-api:base-url') == '/admin/finder-api/'
    assert reverse('admin:finder-api:javascript-catalog') == '/admin/finder-api/jsi18n/'


def test_the_prefix_does_not_collide_with_an_ambit(ambit):
    """`catch_all_view()` resolves `admin/finder/<slug>/`, hence the `finder-api/` prefix."""
    assert reverse('admin:finder-api:base-url').startswith('/admin/finder-api/')


def test_an_anonymous_request_is_not_sent_to_the_login_page(client, ambit):
    """The endpoints are not wrapped in `admin_view()`, so no staff gate applies."""
    response = client.get(reverse('admin:finder-api:base-url'))
    assert response.status_code != 302


def test_a_user_who_is_not_staff_can_read_the_structure(client, ambit):
    user = get_user_model().objects.create_user(username='joe', password='secret')
    assert user.is_staff is False
    client.force_login(user)
    response = client.get(reverse('admin:finder-api:base-url') + f'structure/{ambit.slug}')
    assert response.status_code == 200


def test_the_admin_itself_stays_gated(client):
    assert client.get('/admin/').status_code == 302


def test_a_project_mount_is_preferred_over_the_admin_one():
    """`reverse_api()` resolves either mount; unittests/urls.py provides the direct one."""
    from finder.browser.urls import reverse_api

    assert reverse_api('base-url') == '/finder-api/'


class TestFinderAppIndex:
    """
    `/admin/finder/` lists the configured ambits, each linking into its root folder.

    It is what the “Finder” breadcrumb of `finder/admin/base_site.html` points at.
    """

    def test_it_lists_the_ambits(self, admin_client, ambit):
        response = admin_client.get(reverse('admin:app_list', kwargs={'app_label': 'finder'}))
        assert response.status_code == 200
        assert [app['name'] for app in response.context_data['app_list']] == ['Finder']
        assert response.context_data['title'] == "Finder administration"
        models = response.context_data['app_list'][0]['models']
        assert [model['name'] for model in models] == [ambit.verbose_name]
        assert models[0]['admin_url'] == f'/admin/finder/{ambit.slug}/'

    def test_the_breadcrumb_names_the_app(self, admin_client, ambit):
        html = admin_client.get(reverse('admin:app_list', kwargs={'app_label': 'finder'})).content.decode()
        start = html.index('<div class="breadcrumbs">')
        breadcrumb = ' '.join(html[start:html.index('</div>', start)].split())
        assert breadcrumb == '<div class="breadcrumbs"> <a href="/admin/">Home</a> &rsaquo; Finder'

    def test_another_app_index_is_left_alone(self, admin_client, ambit):
        """The Finder entry must not leak into the index of an unrelated application."""
        response = admin_client.get(reverse('admin:app_list', kwargs={'app_label': 'auth'}))
        assert [app['name'] for app in response.context_data['app_list']] == ["Authentication and Authorization"]

    def test_an_unknown_app_is_still_a_404(self, admin_client, ambit):
        assert admin_client.get('/admin/nosuchapp/').status_code == 404

    def test_the_admin_index_still_lists_finder(self, admin_client, ambit):
        response = admin_client.get(reverse('admin:index'))
        assert 'Finder' in [app['name'] for app in response.context_data['app_list']]
