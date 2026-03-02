from pathlib import Path

from django.core.files.storage import FileSystemStorage
from django.core.files.temp import NamedTemporaryFile


class FinderSystemStorage(FileSystemStorage):
    template = '{id02}/{id24}/{id}/{filename}'

    def __init__(self, template=None, **kwargs):
        if template:
            self.template = template
        super().__init__(**kwargs)

    def path(self, name):
        parts = name.split('/', 1)
        if len(parts) == 1:
            parts.append('')
        name = self.template.format(id=parts[0], id02=parts[0][0:2], id24=parts[0][2:4], filename=parts[1])
        return super().path(name)

    def url(self, name):
        id, filename = name.split('/', 1)
        name = self.template.format(id=id, id02=id[0:2], id24=id[2:4], filename=filename)
        return super().url(name)


def delete_directory(storage, dir_path):
    # Ensure the directory path does not end with a slash for consistency
    dir_path = dir_path.rstrip('/')
    try:
        child_folders, child_files = storage.listdir(dir_path)
    except (FileNotFoundError, OSError):
        # storage.exists() is not supported by all storages for directories
        return
    for entry in child_files:
        try:
            storage.delete(f'{dir_path}/{entry}')
        except (FileNotFoundError, OSError):
            pass
    for entry in child_folders:
        delete_directory(storage, f'{dir_path}/{entry}')
    try:
        storage.delete(dir_path)
    except (FileNotFoundError, OSError):
        pass


def copy_to_local(storage, file_path):
    """
    Copy a file from storage to a local temporary file.
    This is needed because ffmpeg cannot seek in pipe input, and MP4 files
    with the moov atom at the end require seeking to be read properly.
    """
    source_suffix = Path(file_path).suffix
    local_file = NamedTemporaryFile(suffix=source_suffix)
    with storage.open(file_path, 'rb') as handle:
        for chunk in handle.chunks():
            local_file.write(chunk)
    local_file.flush()
    return local_file
