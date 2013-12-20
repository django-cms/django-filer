#-*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied


def check_files_edit_permissions(request, files):
    for f in files:
        if not f.can_edit(request.user):
            raise PermissionDenied


def check_folder_edit_permissions(request, folders):
    for f in folders:
        if not f.can_edit(request.user):
            raise PermissionDenied
        check_files_edit_permissions(request, f.files)
        check_folder_edit_permissions(request, f.children.all())


def check_files_read_permissions(request, files):
    for f in files:
        if not f.can_read(request.user):
            raise PermissionDenied


def check_folder_read_permissions(request, folders):
    for f in folders:
        if not f.can_read(request.user):
            raise PermissionDenied
        check_files_read_permissions(request, f.files)
        check_folder_read_permissions(request, f.children.all())


def userperms_for_request(item, request):
    r = []
    ps = ['read', 'edit']
    for p in ps:
        attr = "can_%s" % p
        if hasattr(item, attr):
            x = getattr(item, attr)(request)
            if x:
                r.append(p)
    return r
