from cmsroles.siteadmin import (is_site_admin, get_user_roles_on_sites_ids,
                                get_administered_sites)
from django.contrib.auth.models import Permission


def has_admin_role(user):

    def _fetch_admin_role():
        is_admin = is_site_admin(user)
        setattr(user, '_is_site_admin', is_admin)
        return is_admin

    return getattr(user, '_is_site_admin', _fetch_admin_role())


def get_roles_on_sites(user):

    def _fetch_roles():
        roles_with_sites = get_user_roles_on_sites_ids(user)
        setattr(user, '_roles_on_sites', roles_with_sites)
        return roles_with_sites

    return getattr(user, '_roles_on_sites', _fetch_roles())


def can_restrict_on_site(user, site):
    site_id = site
    if not isinstance(site, int):
        site_id = getattr(site, 'id', None)

    def _fetch_perm_existance():
        roles_on_site = [role
            for role, site_ids in get_roles_on_sites(user).items()
            if site_id in site_ids]
        return Permission.objects.filter(
            content_type__app_label='filer',
            codename='can_restrict_operations',
            group__role__in=roles_on_site).exists()

    if user.is_superuser or (site_id is None and has_admin_role(user)):
        return True
    if site_id:
        return getattr(user, '_can_restrict_on_site', {}).setdefault(
            site_id, _fetch_perm_existance())
    return False


def get_sites_without_restriction_perm(user):
    if user.is_superuser:
        return []
    return [site
            for site in get_sites_for_user(user)
            if can_restrict_on_site(user, site) is False]


def get_admin_sites_for_user(user):

    def _fetch_admin_sites():
        admin_sites = get_administered_sites(user)
        setattr(user, '_administered_sites', admin_sites)
        return admin_sites

    return getattr(user, '_administered_sites', _fetch_admin_sites())


def has_role_on_site(user, site):
    return user.is_superuser or site.id in get_sites_for_user(user)


def has_admin_role_on_site(user, site):
    return site.id in [_site.id
                       for _site in get_admin_sites_for_user(user)]


def get_sites_for_user(user):
    """
    Returns all sites available for user.
    """
    def _fetch_sites_for_user():
        available_sites = set()
        for sites in get_roles_on_sites(user).values():
            available_sites |= sites
        setattr(user, '_available_sites', available_sites)
        return available_sites

    return getattr(user, '_available_sites', _fetch_sites_for_user())
