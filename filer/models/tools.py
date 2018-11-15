# -*- coding: utf-8 -*-
from __future__ import absolute_import

from . import Clipboard
from ..utils.compatibility import is_authenticated


def discard_clipboard(clipboard):
    clipboard.files.clear()


def delete_clipboard(clipboard):
    for file_obj in clipboard.files.all():
        file_obj.delete()


def get_user_clipboard(user):
    if is_authenticated(user):
        clipboard = Clipboard.objects.get_or_create(user=user)[0]
        return clipboard


def move_file_to_clipboard(files, clipboard):
    count = 0
    for file_obj in files:
        if clipboard.append_file(file_obj):
            file_obj.folder = None
            file_obj.save()
            count += 1
    return count


def move_files_from_clipboard_to_folder(clipboard, folder):
    return move_files_to_folder(clipboard.files.all(), folder)


def move_files_to_folder(files, folder):
    for file_obj in files:
        file_obj.folder = folder
        file_obj.save()
    return True
