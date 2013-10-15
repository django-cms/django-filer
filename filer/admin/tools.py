#-*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from filer.utils.cms_roles import *
from filer.models.foldermodels import Folder


def is_valid_destination(request, folder):
    if folder.is_readonly():
        return False
    user = request.user
    if user.is_superuser:
        return True
    if folder.is_restricted_for_user(request.user):
        return False
    if not folder.site:
        return False
    if folder.site.id in get_sites_for_user(user):
        return True
    return False


def _filter_available_sites(request):
    current_site = request.REQUEST.get('current_site', None)
    user = request.user
    available_sites = get_sites_for_user(user)
    if current_site:
        current_site = int(current_site)
        if not user.is_superuser and current_site not in available_sites:
            available_sites = []
        else:
            available_sites = [current_site]
    return available_sites


def folders_available(request, folders_qs):
    """
    Returns a queryset with folders that current user can see
        * core folders
        * only site folders with sites available to the user
        * site admins can also see site folder files with no site assigned

    * current_site param is passed only with cms plugin change form so this
        will restrict visible files/folder for the ones that belong to that
        site for all users, even superusers
    """
    user = request.user
    current_site = request.REQUEST.get('current_site', None)

    if user.is_superuser and not current_site:
        return folders_qs

    available_sites = _filter_available_sites(request)

    sites_q = Q(Q(folder_type=Folder.CORE_FOLDER) |
                Q(site__in=available_sites))

    if has_admin_role(user) and not current_site:
        sites_q |= Q(site__isnull=True)

    return folders_qs.filter(sites_q)


def files_available(request, files_qs):
    """
    Returns a queryset with files that current user can see:
        * core folder files
        * files from 'unfiled files'
        * only site folder files with sites available to the user
        * site admins can also see site folder files with no site assigned

    * current_site param is passed only with cms plugin change form so this
        will restrict visible files/folder for the ones that belong to that
        site for all users, even superusers
    """
    user = request.user
    current_site = request.REQUEST.get('current_site', None)

    if user.is_superuser and not current_site:
        return files_qs

    available_sites = _filter_available_sites(request)

    sites_q = Q(Q(folder__folder_type=Folder.CORE_FOLDER) |
                Q(folder__site__in=available_sites))

    if not current_site:
        sites_q |= Q(folder__isnull=True)
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

    if not user.has_perm('filer.can_restrict_operations'):
        if files.restricted().exists() or folders.restricted().exists():
            return False

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
