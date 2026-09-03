import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.files.temp import NamedTemporaryFile
from django.utils.module_loading import import_string


class FinderSystemStorage(FileSystemStorage):
    template = '{id02}/{id24}/{id}/{filename}'

    def __init__(self, template=None, **kwargs):
        if template:  # pragma: no cover
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
except ImportError:  # pragma: without django-storages
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


logger = logging.getLogger(__name__)


def derive_storage(alias, default_config):
    """
    Build a `FinderSystemStorage` configuration for `alias` out of the `default` one.

    It keeps whatever the project configured for `default` — the filesystem root and the
    URL prefix — and puts the ambit into a subdirectory named after the alias.
    """
    options = dict(default_config.get('OPTIONS') or {})
    location = options.get('location') or settings.MEDIA_ROOT
    base_url = options.get('base_url') or settings.MEDIA_URL or '/media/'
    return {
        'BACKEND': 'finder.storages.FinderSystemStorage',
        'OPTIONS': {
            'location': str(Path(location) / alias),
            'base_url': f"{base_url.rstrip('/')}/{alias}/",
            # finder rewrites a payload in place when a sanitizing validator changes it,
            # and regenerates samples under a stable name
            'allow_overwrite': True,
        },
    }


def configure_default_storages():
    """
    Add the storages an ambit refers to by default, unless the project declared them.

    A plain `FileSystemStorage` cannot stand in for them: `FinderSystemStorage` shards
    payloads by UUID in `path()` and `url()`, so pointing an ambit at `default` would
    write files where finder will not look for them later.

    Called from `finder.apps.FinderConfig.ready()`, before anything reads `storages`.
    Returns the aliases which had to be derived.
    """
    from finder.models.ambit import AmbitModel

    aliases = [
        AmbitModel._meta.get_field('_original_storage').default,
        AmbitModel._meta.get_field('_sample_storage').default,
    ]
    configured = settings.STORAGES
    default_config = configured.get('default')
    if default_config is None:  # pragma: no cover
        return []
    try:
        backend = import_string(default_config['BACKEND'])
    except ImportError:  # pragma: no cover
        return []
    if not issubclass(backend, FileSystemStorage):
        # a remote default storage carries no location to derive a subdirectory from
        logger.warning(
            "The “default” storage is %s, so the finder storages %s cannot be derived from "
            "it. Declare them in STORAGES.",
            default_config['BACKEND'],
            ', '.join(f'“{alias}”' for alias in aliases if alias not in configured),
        )
        return []

    derived = []
    for alias in aliases:
        if alias in configured:
            continue
        configured[alias] = derive_storage(alias, default_config)
        derived.append(alias)
    if derived:
        _reset_storage_handler()
    return derived


def _reset_storage_handler():
    """
    Drop the cached backends of `django.core.files.storage.storages`.

    Another application may have resolved a storage while its own `ready()` ran, which
    caches `settings.STORAGES` as it was before the aliases above were added. This is what
    Django's own `setting_changed` receiver does when a test overrides STORAGES.
    """
    from django.core.files.storage import storages

    try:
        del storages.backends
    except AttributeError:
        pass
    storages._backends = None
    storages._storages = {}
