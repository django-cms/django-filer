from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import PermissionDenied
from django.utils.http import urlencode


ALLOWED_PICK_TYPES = ('folder', 'file')


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
    return (
        IS_POPUP_VAR in request.GET
        or 'pop' in request.GET
        or IS_POPUP_VAR in request.POST
        or 'pop' in request.POST
    )


def popup_pick_type(request):
    # very important to limit the pick_types because the result is marked safe.
    # (injection attacks)
    pick_type = request.GET.get('_pick', request.POST.get('_pick'))
    if pick_type in ALLOWED_PICK_TYPES:
        return pick_type
    return None


def admin_url_params(request, params=None):
    """
    given a request, looks at GET and POST values to determine which params
    should be added. Is used to keep the context of popup and picker mode.
    """
    params = params or {}
    if popup_status(request):
        params[IS_POPUP_VAR] = '1'
    pick_type = popup_pick_type(request)
    if pick_type:
        params['_pick'] = pick_type
    return params


def admin_url_params_encoded(request, first_separator='?', params=None):
    # sorted to make testing easier
    params = urlencode(
        sorted(admin_url_params(request, params=params).items())
    )
    if not params:
        return ''
    return '{0}{1}'.format(first_separator, params)


class AdminContext(dict):
    def __init__(self, request):
        super().__init__()
        self.update(admin_url_params(request))

    def __missing__(self, key):
        """
        Always allow accessing the keys 'popup', 'pick', 'pick_file' and
        'pick_folder' as keys.
        """
        if key == 'popup':
            return self.get(IS_POPUP_VAR, False) == '1'
        elif key == 'pick':
            return self.get('_pick', '')
        elif key.startswith('pick_'):
            return self.get('_pick', '') == key.split('pick_')[1]

    def __getattr__(self, name):
        """
        Always allow accessing 'popup', 'pick', 'pick_file' and 'pick_folder'
        as attributes.
        """
        if name in ('popup', 'pick') or name.startswith('pick_'):
            return self.get(name)
        raise AttributeError
