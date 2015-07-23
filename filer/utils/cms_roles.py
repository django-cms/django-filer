from django.contrib.sites.models import Site
from cmsroles.siteadmin import (is_site_admin, get_user_roles_on_sites_ids,
                                get_administered_sites)
from django.contrib.auth.models import Permission
from functools import wraps


def get_or_fetch(fetch_func):
    """
        Helper decorator that sets the result of the decorated function on
    a user request object. It is used to minimise the number of queries done
    per request.
    """
    @wraps(fetch_func)
    def wrapper(user, *args, **kwargs):
        attr_name = '_%s' % fetch_func.func_name
        if not hasattr(user, attr_name):
            result = fetch_func(user, *args, **kwargs)
            setattr(user, attr_name, result)
        return getattr(user, attr_name)
    return wrapper

@get_or_fetch
def has_admin_role(user):
    return is_site_admin(user)


@get_or_fetch
def get_roles_on_sites(user):
    return get_user_roles_on_sites_ids(user)


def can_restrict_on_site(user, site):
    site_id = site
    if not unicode(site_id).isnumeric():
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
        if not hasattr(user, '_can_restrict_on_site'):
            setattr(user, '_can_restrict_on_site', {})
        return user._can_restrict_on_site.setdefault(
            site_id, _fetch_perm_existance())
    return False


def get_sites_without_restriction_perm(user):
    if user.is_superuser:
        return []
    return [site
            for site in get_sites_for_user(user)
            if can_restrict_on_site(user, site) is False]


@get_or_fetch
def get_admin_sites_for_user(user):
    admin_sites = get_administered_sites(user)
    return admin_sites


def has_role_on_site(user, site):
    return user.is_superuser or site.id in get_sites_for_user(user)


def has_admin_role_on_site(user, site):
    return site.id in [_site.id
                       for _site in get_admin_sites_for_user(user)]


@get_or_fetch
def get_sites_for_user(user):
    """
    Returns all sites available for user.
    """
    if user.is_superuser:
        return set(Site.objects.values_list('id', flat=True))
    available_sites = set()
    for sites in get_roles_on_sites(user).values():
        available_sites |= sites
    return available_sites
