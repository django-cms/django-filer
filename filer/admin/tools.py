#-*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from cmsroles.siteadmin import (is_site_admin, get_user_roles_on_sites_ids,
                                get_administered_sites)
from django.db.models import Q
from filer.models.foldermodels import Folder


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


def is_valid_destination(request, folder):
    if folder.is_readonly():
        return False
    user = request.user
    if user.is_superuser:
        return True
    if not folder.site:
        return False
    if folder.site.id in get_sites_for_user(user):
        return True
    return False


def folders_available(request, folders_qs):
    """
    Returns a queryset with folders that current user can see
        * core folders
        * only site folders with sites available to the user
        * site admins can also see site folder files with no site assigned
    """
    user = request.user

    if user.is_superuser:
        return folders_qs

    available_sites = get_sites_for_user(user)
    current_site = request.REQUEST.get('folder__site', None)
    if current_site:
        current_site = int(current_site)
        if current_site not in available_sites:
            available_sites = []
        else:
            available_sites = [current_site]

    sites_q = Q(Q(folder_type=Folder.CORE_FOLDER) |
                Q(site__in=available_sites))

    if has_admin_role(user):
        sites_q |= Q(site__isnull=True)

    return folders_qs.filter(sites_q)


def files_available(request, files_qs):
    """
    Returns a queryset with files that current user can see:
        * core folder files
        * files from 'unfiled files'
        * only site folder files with sites available to the user
        * site admins can also see site folder files with no site assigned
    """
    user = request.user

    if user.is_superuser:
        return files_qs

    available_sites = get_sites_for_user(user)
    current_site = request.REQUEST.get('folder__site', None)
    if current_site:
        current_site = int(current_site)
        if current_site not in available_sites:
            available_sites = []
        else:
            available_sites = [current_site]

    sites_q = Q(Q(folder__folder_type=Folder.CORE_FOLDER) |
                Q(folder__site__in=available_sites) |
                Q(folder__isnull=True))

    if has_admin_role(user):
        sites_q |= Q(folder__site__isnull=True)

    return files_qs.filter(sites_q)


def has_multi_file_action_permission(request, files, folders):
    # unfiled files can be moved/deleted so better to just exclude them
    #   from checking permissions for them
    files = files.exclude(folder__isnull=True)

    if files.readonly().exists() or folders.readonly().exists():
        return False
    user = request.user
    if user.is_superuser:
        return True
    # only superusers can move/delete files/folders with no site ownership
    if (files.filter(folder__site__isnull=True).exists() or
            folders.filter(site__isnull=True).exists()):
        return False

    _exists_root_folders = folders.filter(parent__isnull=True).exists()
    if _exists_root_folders:
        if not has_admin_role(user):
            return False
        # allow site admins to move/delete root files/folders that belong
        #   to the site where is admin
        sites_allowed = [s.id for s in get_admin_sites_for_user(user)]
    else:
        sites_allowed = get_sites_for_user(user)

    if (files.exclude(folder__site__in=sites_allowed).exists() or
            folders.exclude(site__in=sites_allowed).exists()):
        return False

    return True
