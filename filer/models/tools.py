#-*- coding: utf-8 -*-
from filer.models import Clipboard


def discard_clipboard(clipboard):
    clipboard.files.clear()


def delete_clipboard(clipboard):
    for file in clipboard.files.all():
        file.delete()


def get_user_clipboard(user):
    if user.is_authenticated():
        clipboard = Clipboard.objects.get_or_create(user=user)[0]
        return clipboard


def move_file_to_clipboard(files, clipboard):
    for file in files:
        clipboard.append_file(file)
        file.folder = None
        file.save()
    return True


def move_files_from_clipboard_to_folder(clipboard, folder):
    return move_files_to_folder(clipboard.files.all(), folder)


def move_files_to_folder(files, folder):
    for file in files:
        file.folder = folder
        file.save()
    return True
