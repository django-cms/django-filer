from cmsroles.siteadmin import (is_site_admin, get_user_roles_on_sites_ids,
                                get_administered_sites)

def has_admin_role(user):

    def _fetch_admin_role():
        is_admin = is_site_admin(user)
        setattr(user, '_is_site_admin', is_admin)
        return is_admin

    return getattr(user, '_is_site_admin', _fetch_admin_role())


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
        for sites in get_user_roles_on_sites_ids(user).values():
            available_sites |= sites
        setattr(user, '_available_sites', available_sites)
        return available_sites

    return getattr(user, '_available_sites', _fetch_sites_for_user())
