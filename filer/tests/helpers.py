#-*- coding: utf-8 -*-
from PIL import Image, ImageChops, ImageDraw

from django.contrib.auth.models import User
from filer.models.foldermodels import Folder
from filer.models.clipboardmodels import Clipboard, ClipboardItem

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
