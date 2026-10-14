from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import PermissionDenied
from django.db import connections
from django.utils.http import urlencode

from .. import settings
from ..models import File, Folder


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
    # Walk one tree level at a time so queries grow with depth, not size.
    # Per-object checks still decide, so model overrides keep working.
    level = list(folders)
    seen = set()
    while level:
        level_by_id = {}
        for folder in level:
            if not getattr(folder, check)(request):
                raise PermissionDenied
            level_by_id[folder.pk] = folder
        seen.update(level_by_id)

        for file_obj in filter_in_batches(File.objects.all(), 'folder_id', level_by_id):
            # Reuse the loaded folder and its permission cache.
            file_obj.folder = level_by_id[file_obj.folder_id]
            if not getattr(file_obj, check)(request):
                raise PermissionDenied

        children = filter_in_batches(Folder.objects.all(), 'parent_id', level_by_id)
        level = [child for child in children if child.pk not in seen]


def load_subtrees(folders):
    """
    Load everything below ``folders``, one tree level per query.

    Returns ``(children, files)``, mapping folder ids to child folders (by
    name) and to their files. Loaded rows share their parent instances.
    """
    children, files = {}, {}
    level = {folder.pk: folder for folder in folders}
    seen = set(level)
    while level:
        for file_obj in filter_in_batches(File.objects.all(), 'folder_id', level):
            file_obj.folder = level[file_obj.folder_id]
            files.setdefault(file_obj.folder_id, []).append(file_obj)

        next_level = {}
        for child in filter_in_batches(Folder.objects.order_by('name'), 'parent_id', level):
            if child.pk in seen:
                continue

            child.parent = level[child.parent_id]
            children.setdefault(child.parent_id, []).append(child)
            next_level[child.pk] = child
        seen.update(next_level)
        level = next_level
    return children, files


def attach_ancestors(folders):
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


def filter_in_batches(queryset, field, ids):
    # Stay below the database's query parameter limit, e.g. 999 on SQLite.
    ids = list(ids)
    batch_size = connections[queryset.db].features.max_query_params or len(ids) or 1
    for offset in range(0, len(ids), batch_size):
        yield from queryset.filter(**{f'{field}__in': ids[offset:offset + batch_size]})


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
