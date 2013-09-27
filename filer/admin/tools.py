#-*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied
from cmsroles.siteadmin import is_site_admin, get_user_roles_on_sites_ids
from django.db.models import Q
from filer.models.foldermodels import Folder


def check_files_edit_permissions(request, files):
    for f in files:
        if not f.has_edit_permission(request):
            raise PermissionDenied


def check_folder_edit_permissions(request, folders):
    for f in folders:
        if not f.has_edit_permission(request):
            raise PermissionDenied
        check_files_edit_permissions(request, f.files)
        check_folder_edit_permissions(request, f.children.all())


def check_files_read_permissions(request, files):
    for f in files:
        if not f.has_read_permission(request):
            raise PermissionDenied


def check_folder_read_permissions(request, folders):
    for f in folders:
        if not f.has_read_permission(request):
            raise PermissionDenied
        check_files_read_permissions(request, f.files)
        check_folder_read_permissions(request, f.children.all())


def userperms_for_request(item, request):
    r = []
    ps = ['read', 'edit', 'add_children']
    for p in ps:
        attr = "has_%s_permission" % p
        if hasattr(item, attr):
            x = getattr(item, attr)(request)
            if x:
                r.append(p)
    return r


def _get_sites_for_user(user):
    """
    Returns all sites available for user.
    This also binds the sites to the user in order to save some
        queries execution
    """
    available_sites = set()
    for sites in get_user_roles_on_sites_ids(user).values():
        available_sites |= sites
    setattr(user, '_available_sites', available_sites)
    return available_sites


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

    sites = getattr(user, '_available_sites', _get_sites_for_user(user))
    sites_q = Q(Q(folder_type=Folder.CORE_FOLDER) |
                Q(site__in=sites))

    if is_site_admin(user):
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

    sites = getattr(user, '_available_sites', _get_sites_for_user(user))
    sites_q = Q(Q(folder__folder_type=Folder.CORE_FOLDER) |
                Q(folder__site__in=sites) | Q(folder__isnull=True))

    if is_site_admin(user):
        sites_q |= Q(folder__site__isnull=True)

    return files_qs.filter(sites_q)
