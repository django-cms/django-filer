from functools import wraps

from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from filer.settings import FILER_ROLES_MANAGER


def get_roles_manager():
    if hasattr(get_roles_manager, '_cache'):
        return get_roles_manager._cache
    try:
        if callable(FILER_ROLES_MANAGER):
            manager = FILER_ROLES_MANAGER()
        manager = import_string(FILER_ROLES_MANAGER)()
    except ImportError:
        err_msg = ("Cannot import {}! This should be a manager for permissions."
                   "Please consult documentation.".format(FILER_ROLES_MANAGER))
        raise ImproperlyConfigured(err_msg)
    get_roles_manager._cache = manager
    return manager


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
    return get_roles_manager().is_site_admin(user)


def can_restrict_on_site(user, site):
    site_id = site
    if not unicode(site_id).isnumeric():
        site_id = getattr(site, 'id', None)

    def _fetch_perm_existance():
        manager = get_roles_manager()
        return manager.has_perm_on_site(user, site_id, 'filer.can_restrict_operations')

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
    return get_roles_manager().get_administered_sites(user)


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
    return get_roles_manager().get_accessible_sites(user)
