#-*- coding: utf-8 -*-
from django.contrib import messages

from filer.models import Clipboard
from filer import settings


def discard_clipboard(clipboard):
    clipboard.files.clear()


def delete_clipboard(clipboard):
    for file_obj in clipboard.files.all():
        file_obj.delete()


def get_user_clipboard(user):
    if user.is_authenticated():
        clipboard = Clipboard.objects.get_or_create(user=user)[0]
        return clipboard


def move_file_to_clipboard(request, files, clipboard):
    count = 0
    if settings.FOLDER_AFFECTS_URL:
        file_names = [f.original_filename for f in files]
        already_existing = [
            f.original_filename
            for f in clipboard.files.filter(original_filename__in=file_names)]
    for file_obj in files:
        if settings.FOLDER_AFFECTS_URL and file_obj.original_filename in already_existing:
            messages.error(request, 'Clipboard already contains a file '
                           'named %s' % file_obj.display_name)
            continue
        if clipboard.append_file(file_obj):
            file_obj .folder = None
            file_obj.save()
            count += 1
    return count


def move_files_from_clipboard_to_folder(request, clipboard, folder):
    return move_files_to_folder(request, clipboard.files.all(), folder)


def move_files_to_folder(request, files, folder):
    if settings.FOLDER_AFFECTS_URL:
        file_names = [f.display_name for f in files]
        already_existing = [
            f.display_name 
            for f in folder.files_and_folders_with_names(file_names)]
    for file_obj in files:
        if settings.FOLDER_AFFECTS_URL and file_obj.display_name in already_existing:
            messages.error(request, "File or folder named %s already exists" % file_obj.display_name)
            continue
        file_obj.folder = folder
        file_obj.save()
    return True
