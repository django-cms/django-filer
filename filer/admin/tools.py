from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import PermissionDenied
from django.utils.http import urlencode

from .. import settings
from ..utils.queries import filter_in_batches
from ..utils.tree import walk_folder_levels as _walk_folder_levels


ALLOWED_PICK_TYPES = ('folder', 'file')


def check_files_edit_permissions(request, files):
    for f in files:
        if not f.has_edit_permission(request):
            raise PermissionDenied


def check_folder_edit_permissions(request, folders):
    _check_folder_tree(request, folders, 'has_edit_permission')


def has_admin_read_permission(request, item):
    """
    Return whether ``item`` may be disclosed to the user in the admin.

    This is ``item.has_read_permission()`` plus the exception the directory
    listing already makes: unfiled files (``folder`` is ``NULL``) are a shared
    inbox and are deliberately listed for every user of the file browser, see
    the queryset filter in ``FolderAdmin.directory_listing()``. Without that
    exception, checking read permissions would hide the icons and change views
    of files the listing does show.
    """
    if hasattr(item, 'folder_id') and item.folder_id is None:
        return True
    return bool(item.has_read_permission(request))


def check_files_read_permissions(request, files):
    for f in files:
        if not f.has_read_permission(request):
            raise PermissionDenied


def check_folder_read_permissions(request, folders):
    _check_folder_tree(request, folders, 'has_read_permission')


def _check_folder_tree(request, folders, check):
    # Check the same instances used by the shared traversal.
    for level, files in walk_subtrees(folders):
        for folder in level.values():
            if not getattr(folder, check)(request):
                raise PermissionDenied
        for file_obj in files:
            if not getattr(file_obj, check)(request):
                raise PermissionDenied
        del files


def walk_folder_levels(folders, accept=None):
    """Walk visible folders, pruning rejected subtrees and sharing parents."""
    from ..models import Folder

    def link(child, level):
        child.parent = level[child.parent_id]
        if accept is None or accept(child):
            return child.pk, child
        return None

    roots = {folder.pk: folder for folder in folders if accept is None or accept(folder)}
    yield from _walk_folder_levels(roots, Folder.objects.all(), link)


def walk_subtrees(folders):
    """Yield folders and files one level at a time, sharing parent instances."""
    from ..models import File

    for level in walk_folder_levels(folders):
        files = []
        for file_obj in filter_in_batches(File.objects.all(), 'folder_id', level):
            file_obj.folder = level[file_obj.folder_id]
            files.append(file_obj)
        yield level, files
        del files


def attach_ancestors(folders):
    from ..models import Folder

    # Share one instance per ancestor, loading one tree level per query.
    known = {folder.pk: folder for folder in folders}
    level = list(folders)
    while level:
        missing = {folder.parent_id for folder in level if folder.parent_id is not None} - known.keys()
        loaded = list(filter_in_batches(Folder.objects.all(), 'pk', missing))
        known.update((folder.pk, folder) for folder in loaded)
        for folder in level:
            if folder.parent_id is not None:
                folder.parent = known[folder.parent_id]
        level = loaded


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


def edit_from_widget(request):
    return request.GET.get('_edit_from_widget') == '1'


def get_directory_listing_type(request):
    list_type = request.GET.get('_list_type', None)
    if list_type not in settings.FILER_FOLDER_ADMIN_LIST_TYPE_CHOICES:
        return
    return list_type


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
    if edit_from_widget(request):
        params['_edit_from_widget'] = '1'
    list_type = get_directory_listing_type(request)
    if list_type and '_list_type' not in params.keys():
        params['_list_type'] = list_type
    return params


def admin_url_params_encoded(request, first_separator='?', params=None):
    # sorted to make testing easier
    params = urlencode(
        sorted(admin_url_params(request, params=params).items())
    )
    if not params:
        return ''
    return f'{first_separator}{params}'


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
