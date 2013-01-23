#-*- coding: utf-8 -*-
from filer.models import Clipboard
from filer import settings as filer_settings


def discard_clipboard(clipboard):
    clipboard.files.clear()


def delete_clipboard(clipboard):
    for file_obj in clipboard.files.all():
        file_obj.delete()


def get_user_clipboard(user):
    if user.is_authenticated():
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
        if file_obj.is_public:
            upload_to = filer_settings.FILER_PUBLICMEDIA_UPLOAD_TO
        else:
            upload_to = filer_settings.FILER_PRIVATEMEDIA_UPLOAD_TO

        storage = file_obj.file.storage
        file_obj.folder = folder
        new_location = upload_to(file_obj, file_obj.original_filename)
        new_name = storage.save(new_location, file_obj.file.file)
        storage.delete(file_obj.file.name)
        file_obj.file.name = new_name
        file_obj.save()
    return True
