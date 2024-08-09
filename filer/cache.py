from django.core.cache import cache


def get_folder_perm_cache_key(user, permission):
    return f"filer:perm:{permission}"


def get_folder_permission_cache(user, permission):
    cache_value = cache.get(get_folder_perm_cache_key(user, permission))
    if cache_value:
        return cache_value.get(user.pk, None)
    return None


def clear_folder_permission_cache(user, permission=None):
    if permission is None:
        for perm in ['can_read', 'can_edit', 'can_add_children']:
            cache.delete(get_folder_perm_cache_key(user, perm))
    else:
        cache.delete(get_folder_perm_cache_key(user, permission))


def update_folder_permission_cache(user, permission, id_list):
    perms = get_folder_permission_cache(user, permission) or {}
    perms[user.pk] = id_list
    cache.set(get_folder_perm_cache_key(user, permission), perms)
