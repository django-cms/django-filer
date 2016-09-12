#-*- coding: utf-8 -*-
from django.contrib import messages
from django.utils.translation import ugettext as _

from filer.models import Clipboard


def discard_clipboard(clipboard):
    clipboard.files.clear()

def discard_clipboard_files(clipboard, files):
    clipboard.clipboarditem_set.filter(file__in=files).delete()


def delete_clipboard(clipboard):
    for file_obj in clipboard.files.all():
        file_obj.delete()


def get_user_clipboard(user):
    if user.is_authenticated():
        clipboard = Clipboard.objects.get_or_create(user=user)[0]
        return clipboard


def move_file_to_clipboard(request, files, clipboard):
    count = 0
    file_names = [f.clean_actual_name for f in files]
    already_existing = [
        f.clean_actual_name
        for f in clipboard.files.all() if f.clean_actual_name in file_names]
    for file_obj in files:
        if file_obj.clean_actual_name in already_existing:
            messages.error(request, _(u'Clipboard already contains a file '
                                      'named %s') % file_obj.clean_actual_name)
            continue
        if clipboard.append_file(file_obj):
            file_obj.folder = None
            file_obj.save()
            count += 1
    return count


def move_files_from_clipboard_to_folder(request, clipboard, folder):
    return move_files_to_folder(request, clipboard.files.all(), folder)


def split_files_valid_for_destination(files, destination):
    file_names = [f.clean_actual_name for f in files]
    already_existing = [
        f.clean_actual_name
        for f in destination.entries_with_names(file_names)]

    valid_files, invalid_files = [], []
    for file_obj in files:
        if file_obj.clean_actual_name in already_existing:
            invalid_files.append(file_obj)
        else:
            valid_files.append(file_obj)
    return valid_files, invalid_files


def move_files_to_folder(request, files, destination):
    valid_files, invalid_files = split_files_valid_for_destination(
        files, destination)

    for file_obj in valid_files:
        file_obj.folder = destination
        file_obj.save()

    for file_obj in invalid_files:
        messages.error(
            request, _(u"File or folder named %s already exists in "
                       "this folder.") % file_obj.clean_actual_name)
    return valid_files
