import datetime
import os

import filer.models.clipboardmodels
from filer.utils.files import get_valid_filename
from filer import settings as filer_settings

from django.core.files.uploadedfile import UploadedFile
from django.utils.encoding import force_unicode, smart_str

def by_date(instance, filename):
    datepart = force_unicode(datetime.datetime.now().strftime(smart_str("%Y/%m/%d")))
    return os.path.join(datepart, get_valid_filename(filename))


class prefixed_factory(object):
    def __init__(self, upload_to, prefix):
        self.upload_to = upload_to
        self.prefix = prefix

    def __call__(self, instance, filename):
        if callable(self.upload_to):
            upload_to_str = self.upload_to(instance, filename)
        else:
            upload_to_str = self.upload_to
        if not self.prefix:
            return upload_to_str
        return os.path.join(self.prefix, upload_to_str)


def _is_in_memory(file_):
    return isinstance(file_, UploadedFile)


def _construct_logical_folder_path(filer_file):
    return os.path.join(*(folder.name for folder in filer_file.logical_path))


def _goes_to_clipboard(instance):
    return instance.folder is None or (
        instance.pk is None and _is_in_memory(instance.file.file))


def by_path(instance, filename):
    if _goes_to_clipboard(instance):
        return os.path.join(
            filer.models.clipboardmodels.Clipboard.folder_name,
            instance.owner.username,
            filename)
    else:
        return os.path.join(
            _construct_logical_folder_path(instance),
            instance.actual_name)


def get_trash_path(instance):
    path = [filer_settings.FILER_TRASH_PREFIX]
    # enforce uniqueness by using file's pk
    path.append("%s" % instance.pk)
    # add folder path
    path.append(instance.pretty_logical_path.strip('/'))
    return os.path.join(*path)
