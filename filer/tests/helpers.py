#-*- coding: utf-8 -*-
from PIL import Image, ImageChops, ImageDraw

from django.contrib.auth.models import User, Permission
from filer.models.foldermodels import Folder, FolderPermission
from filer.models.clipboardmodels import Clipboard, ClipboardItem
from contextlib import contextmanager


@contextmanager
def login_using(client, user_type=None):
    username = 'login_using_foo'
    password = 'secret'
    user = User.objects.create_user(username=username, password=password)
    if user_type == 'superuser':
        user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.save()
    client.login(username=username, password=password)
    yield
    client.logout()
    user.delete()


def create_superuser():
    superuser = User.objects.create_superuser('admin',
                                              'admin@free.fr',
                                              'secret')
    return superuser

def create_folder_structure(depth=2, sibling=2, parent=None):
    """
    This method creates a folder structure of the specified depth.

    * depth: is an integer (default=2)
    * sibling: is an integer (default=2)
    * parent: is the folder instance of the parent.
    """
    if depth > 0 and sibling > 0:
        depth_range = range(1, depth+1)
        depth_range.reverse()
        for d in depth_range:
            for s in range(1,sibling+1):
                name = "folder: %s -- %s" %(str(d), str(s))
                folder = Folder(name=name, parent=parent)
                folder.save()
                create_folder_structure(depth=d-1, sibling=sibling, parent=folder)

def create_clipboard_item(user, file_obj):
    clipboard, was_clipboard_created = Clipboard.objects.get_or_create(user=user)
    clipboard_item = ClipboardItem(clipboard=clipboard, file=file_obj)
    return clipboard_item

def create_image(mode='RGB', size=(800, 600)):
    image = Image.new(mode, size)
    draw = ImageDraw.Draw(image)
    x_bit, y_bit = size[0] // 10, size[1] // 10
    draw.rectangle((x_bit, y_bit * 2, x_bit * 7, y_bit * 3), 'red')
    draw.rectangle((x_bit * 2, y_bit, x_bit * 3, y_bit * 8), 'red')
    return image


class SettingsOverride(object):
    """
    Overrides Django settings within a context and resets them to their inital
    values on exit.

    Example:

        with SettingsOverride(DEBUG=True):
            # do something
    """

    def __init__(self, settings_module, **overrides):
        self.settings_module = settings_module
        self.overrides = overrides

    def __enter__(self):
        self.old = {}
        for key, value in self.overrides.items():
            self.old[key] = getattr(self.settings_module, key, None)
            setattr(self.settings_module, key, value)

    def __exit__(self, type, value, traceback):
        for key, value in self.old.items():
            if value is not None:
                setattr(self.settings_module, key, value)
            else:
                delattr(self.settings_module,key)


def create_staffuser(user):
    user = User.objects.create_user(
        username=user,
        password='secret',
    )
    user.is_staff = True
    user.is_active = True
    user.save()
    return user


def create_folder_for_user(foldername, user):
    folder = Folder.objects.create(
        name=foldername,
        owner=user,
    )
    return folder


def create_folderpermission_for_user(folder, user):
    folder_permission = FolderPermission.objects.create(
        folder=folder,
        type=FolderPermission.CHILDREN,
        user=user,
        can_edit=FolderPermission.ALLOW,
        can_read=FolderPermission.ALLOW,
        can_add_children=FolderPermission.ALLOW,
    )
    return folder_permission


def grant_all_folderpermissions_for_group(group):
    permission_set = Permission.objects.filter(
        codename__endswith='folderpermission',
    )
    for permission in permission_set:
        group.permissions.add(permission)
