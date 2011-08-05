#-*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied


def popup_status(request):
    return '_popup' in request.REQUEST or 'pop' in request.REQUEST


def selectfolder_status(request):
    return 'select_folder' in request.REQUEST


def popup_param(request):
    if popup_status(request):
        return "?_popup=1"
    else:
        return ""


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
