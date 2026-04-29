import uuid
from pathlib import Path

from django.core.cache import cache
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
        id = str(uuid.UUID(parts[0]))  # enforce valid UUID
        filename = '' if len(parts) == 1 else parts[1]
        name = self.template.format(id=id, id02=id[0:2], id24=id[2:4], filename=filename)
        return super().path(name)

    def url(self, name):
        id, filename = name.split('/', 1)
        name = self.template.format(id=id, id02=id[0:2], id24=id[2:4], filename=filename)
        return super().url(name)


try:
    from storages.backends.s3 import S3Storage
except ImportError:
    pass
else:
    class FinderS3Storage(S3Storage):
        """
        Custom S3 storage that caches the result of the exists()-method to prevent multiple HEAD requests
        to the S3 server for lookups of the same file.
        """
        FILE_EXISTS_CACHE_TIMEOUT = 86400  # 1 day

        def exists(self, name):
            key = f'{self.__class__.__name__}:{name}'
            result = cache.get(key)
            if result is None:
                result = super().exists(name)
                if result is True:
                    cache.set(key, True, timeout=self.FILE_EXISTS_CACHE_TIMEOUT)
            return result


def delete_directory(storage, dir_path):
    # Ensure the directory path does not end with a slash for consistency
    dir_path = dir_path.rstrip('/')
    try:
        child_folders, child_files = storage.listdir(dir_path)
    except FileNotFoundError:
        # storage.exists() is not supported by all storages for directories
        return
    for entry in child_files:
        try:
            storage.delete(f'{dir_path}/{entry}')
        except FileNotFoundError:
            pass
    for entry in child_folders:
        delete_directory(storage, f'{dir_path}/{entry}')
    try:
        storage.delete(dir_path)
    except FileNotFoundError:
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
