import typing

from django.core.cache import cache
from django.db.models import Model


UserModel = typing.TypeVar('UserModel', bound=Model)


def get_folder_perm_cache_key(user: UserModel, permission: str) -> str:
    """
    Generates a unique cache key for a given user and permission.

    The key is a string in the format "filer:perm:<permission>", i.e. it does not
    contain the user id. This will be sufficient for most use cases.

    Patch this method to include the user id in the cache key if necessary, e.g.,
    for far more than 1,000 admin users to make the cached unit require less memory.

    Parameters:
    user (UserModel): The user for whom the cache key is being generated.
        The `user` can be an instance of the default `django.contrib.auth.models.User`
        or any custom user model specified by `AUTH_USER_MODEL` in the settings.
    permission (str): The permission for which the cache key is being generated.

    Returns:
    str: The generated cache key.
    """
    return f"filer:perm:{permission}"


def get_folder_permission_cache(user: UserModel, permission: str) -> typing.Optional[dict]:
    """
    Retrieves the cached folder permissions for a given user and permission.

    If the cache value exists, it returns the permissions for the user.
    If the cache value does not exist, it returns None.

    Parameters:
    user (UserModel): The user for whom the permissions are being retrieved.
        The `user` can be an instance of the default `django.contrib.auth.models.User`
        or any custom user model specified by `AUTH_USER_MODEL` in the settings.
    permission (str): The permission for which the permissions are being retrieved.

    Returns:
    dict or None: The permissions for the user, or None if no cache value exists.
    """
    cache_value = cache.get(get_folder_perm_cache_key(user, permission))
    if cache_value:
        return cache_value.get(user.pk, None)
    return None


def clear_folder_permission_cache(user: UserModel, permission: typing.Optional[str] = None) -> None:
    """
    Clears the cached folder permissions for a given user.

    If a specific permission is provided, it clears the cache for that permission only.
    If no specific permission is provided, it clears the cache for all permissions.

    Parameters:
    user (UserModel): The user for whom the permissions are being cleared.
        The `user` can be an instance of the default `django.contrib.auth.models.User`
        or any custom user model specified by `AUTH_USER_MODEL` in the settings.
    permission (str, optional): The specific permission to clear. Defaults to None.
    """
    if permission is None:
        for perm in ['can_read', 'can_edit', 'can_add_children']:
            cache.delete(get_folder_perm_cache_key(user, perm))
    else:
        cache.delete(get_folder_perm_cache_key(user, permission))


def update_folder_permission_cache(user: UserModel, permission: str, id_list: typing.List[int]) -> None:
    """
    Updates the cached folder permissions for a given user and permission.

    It first retrieves the current permissions from the cache (or an empty dictionary if none exist).
    Then it updates the permissions for the user with the provided list of IDs.
    Finally, it sets the updated permissions back into the cache.

    Parameters:
    user (UserModel): The user for whom the permissions are being updated.
        The `user` can be an instance of the default `django.contrib.auth.models.User`
        or any custom user model specified by `AUTH_USER_MODEL` in the settings.
    permission (str): The permission to update.
    id_list (list): The list of IDs to set as the new permissions.
    """
    perms = get_folder_permission_cache(user, permission) or {}
    perms[user.pk] = id_list
    cache.set(get_folder_perm_cache_key(user, permission), perms)
