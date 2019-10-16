#-*- coding: utf-8 -*-
from PIL import Image, ImageChops, ImageDraw

from django.contrib.auth.models import User, Permission
from filer.models.foldermodels import Folder
from filer.models.clipboardmodels import Clipboard, ClipboardItem
from django.core.urlresolvers import reverse
from django.contrib.admin import helpers


def get_dir_listing_url(folder):
    if folder is None:
        return reverse('admin:filer-directory_listing-root')
    if folder is 'unfiled':
        return reverse('admin:filer-directory_listing-unfiled_images')
    return reverse('admin:filer-directory_listing',
                   kwargs={'folder_id': folder.id})

def get_make_root_folder_url():
    return reverse('admin:filer-directory_listing-make_root_folder')


def filer_obj_as_checkox(filer_obj):

    def filer_object_type(filer_obj):
        if isinstance(filer_obj, Folder):
            return 'folder'
        return 'file'

    return '%s-%d' % (filer_object_type(filer_obj), filer_obj.id)


def paste_clipboard_to_folder(client, destination, clipboard):
    data_to_post = { 'clipboard_id': clipboard.pk }
    if destination:
        data_to_post['folder_id'] = destination.id
    return client.post(
        reverse('admin:filer-paste_clipboard_to_folder'), data_to_post)


def move_single_file_to_clipboard_action(client, folder_view, file_to_move):
    post_data = {"move-to-clipboard-%d" % (f.id,): ''
                 for f in file_to_move}
    url = get_dir_listing_url(folder_view)
    return client.post(url, post_data)


def move_to_clipboard_action(client, folder_view, to_move, follow=False):
    objects_to_move = [filer_obj_as_checkox(filer_obj)
                       for filer_obj in to_move]
    url = get_dir_listing_url(folder_view)
    return client.post(url, {
        'action': 'move_to_clipboard',
        'post': 'yes',
        helpers.ACTION_CHECKBOX_NAME: objects_to_move }, follow=follow), url


def move_action(client, folder_view, destination, to_move, follow=False):
    objects_to_move = [filer_obj_as_checkox(filer_obj)
                       for filer_obj in to_move]
    url = get_dir_listing_url(folder_view)
    return client.post(url, {
        'action': 'move_files_and_folders',
        'post': 'yes',
        'destination': destination.id,
        helpers.ACTION_CHECKBOX_NAME: objects_to_move }, follow=follow), url


def enable_restriction(client, folder_view, filer_objects, follow=True):
    url = get_dir_listing_url(folder_view)
    return client.post(url, {
        'action': 'enable_restriction',
        'post': 'yes',
        helpers.ACTION_CHECKBOX_NAME: [filer_obj_as_checkox(obj) for obj in filer_objects]},
                       follow=follow), url


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
        depth_range = list(range(1, depth+1))
        depth_range.reverse()
        for d in depth_range:
            for s in range(1,sibling+1):
                name = "%s -- %s" %(str(d), str(s))
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

    def __call__(self, func):
        if isinstance(func, type):
            def _pre_setup(test_instance):
                self.enable()
                func.setUp(test_instance)
            def _post_teardown(test_instance):
                func.tearDown(test_instance)
                self.disable()
            # preserve cls name for tests discovery tools
            inner = type(func.__name__, (func,), {
                    'setUp': _pre_setup,
                    'tearDown': _post_teardown,
                    '__module__': func.__module__,
                })
            return inner
        else:
            @wraps(func)
            def inner(*args, **kwargs):
                with self:
                    return func(*args, **kwargs)
            return inner


    def enable(self):
        self.old = {}
        for key, value in list(self.overrides.items()):
            self.old[key] = getattr(self.settings_module, key, None)
            setattr(self.settings_module, key, value)

    def disable(self):
       for key, value in list(self.old.items()):
            if value is not None:
                setattr(self.settings_module, key, value)
            else:
                delattr(self.settings_module,key)

    def __enter__(self):
        self.enable()

    def __exit__(self, type, value, traceback):
        self.disable()


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


def get_user_message(response):
    """Helper method to return message from response """
    for c in response.context:
        message = [m for m in c.get('messages')][0]
        if message:
            return message
