#-*- coding: utf-8 -*-
from django.contrib import messages
from django.utils.translation import ugettext as _

from filer.models import Clipboard


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
    file_names = [f.actual_name for f in files]
    already_existing = [
        f.actual_name
        for f in clipboard.files.all() if f.actual_name in file_names]
    for file_obj in files:
        if file_obj.actual_name in already_existing:
            messages.error(request, _(u'Clipboard already contains a file '
                                      'named %s') % file_obj.actual_name)
            continue
        if clipboard.append_file(file_obj):
            file_obj .folder = None
            file_obj.save()
            count += 1
    return count


def move_files_from_clipboard_to_folder(request, clipboard, folder):
    return move_files_to_folder(request, clipboard.files.all(), folder)


def move_files_to_folder(request, files, folder):
    file_names = [f.actual_name for f in files]
    already_existing = [
        f.actual_name 
        for f in folder.entries_with_names(file_names)]
    for file_obj in files:
        if file_obj.actual_name in already_existing:
            messages.error(request, _(u"File or folder named %s already exists") % file_obj.actual_name)
            file_obj.delete()
            continue
        file_obj.folder = folder
        file_obj.save()
    return True
