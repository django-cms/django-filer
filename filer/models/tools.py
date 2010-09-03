from filer.models import Clipboard

def discard_clipboard(clipboard):
    clipboard.files.clear()

def delete_clipboard(clipboard):
    for file in clipboard.files.all():
        file.delete()

def get_user_clipboard(user):
    if user.is_authenticated():
        clipboard, was_clipboard_created = Clipboard.objects.get_or_create(user=user)
        return clipboard

def move_file_to_clipboard(files, clipboard):
    for file in files:
        clipboard.append_file(file)
        file.folder = None
        file.save()
    return True

def clone_files_from_clipboard_to_folder(clipboard, folder):
    for file in clipboard.files.all():
        cloned_file = file.clone()
        cloned_file.folder = folder
        cloned_file.save()

def move_files_from_clipboard_to_folder(clipboard, folder):
    return move_files_to_folder(clipboard.files.all(), folder)


def move_files_to_folder(files, folder):
    for file in files:
        #print "moving %s (%s) to %s" % (file, type(file), folder)
        file.folder = folder
        file.save()
    return True
