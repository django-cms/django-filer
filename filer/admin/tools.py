# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.core.exceptions import PermissionDenied
from django.contrib.admin.options import IS_POPUP_VAR
from ..utils.compatibility import (
    LTE_DJANGO_1_7, LTE_DJANGO_1_6, urlencode)


ALLOWED_PICK_TYPES = ('folder', 'file')


if LTE_DJANGO_1_6:
    def admin_each_context(admin_site, request):
        return {}
elif LTE_DJANGO_1_7:
    def admin_each_context(admin_site, request):
        return admin_site.each_context()
else:
    def admin_each_context(admin_site, request):
        return admin_site.each_context(request)


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


def popup_status(request):
    return (IS_POPUP_VAR in request.GET or 'pop' in request.GET or
            IS_POPUP_VAR in request.POST or 'pop' in request.POST)


def popup_pick_type(request):
    # very important to limit the pick_types because the result is marked safe.
    # (injection attacks)
    pick_type = request.GET.get('_pick', request.POST.get('_pick', None))
    if pick_type in ALLOWED_PICK_TYPES:
        return pick_type
    return None


def admin_url_params(request):
    """
    given a request, looks at GET and POST values to determine which params
    should be added. Is used to keep the context of popup and picker mode.
    """
    # FIXME: put this code in a better location
    params = {}
    if popup_status(request):
        params[IS_POPUP_VAR] = '1'
    pick_type = popup_pick_type(request)
    if pick_type:
        params['_pick'] = pick_type
    return params


def admin_url_params_encoded(request, first_separator='?'):
    # sorted to make testing easier
    params = urlencode(sorted(admin_url_params(request).items()))
    if not params:
        return ''
    return '{0}{1}'.format(first_separator, params)


class AdminUrlParams(dict):
    def __init__(self, request):
        super(AdminUrlParams, self).__init__()
        self.request = request
        self.update(admin_url_params(request))
        extra = dict()
        extra['popup'] = self.get(IS_POPUP_VAR, False) == '1'
        extra['pick'] = self.get('_pick', '')
        for pick_type in ALLOWED_PICK_TYPES:
            extra['pick_{0}'.format(pick_type)] = extra['pick'] == pick_type
        for key, value in extra.items():
            setattr(self, key, value)
        self.update(extra)
