#-*- coding: utf-8 -*-
from django.core.files.base import File
from django.core.files.storage import Storage
from easy_thumbnails import fields as easy_thumbnails_fields, \
    files as easy_thumbnails_files
from filer import settings as filer_settings
from filer.utils.filer_easy_thumbnails import ThumbnailerNameMixin

STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_STORAGE,
}
THUMBNAIL_STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_THUMBNAIL_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE,
}


def generate_filename_multistorage(instance, filename):
    if instance.is_public:
        upload_to = filer_settings.FILER_PUBLICMEDIA_UPLOAD_TO
    else:
        upload_to = filer_settings.FILER_PRIVATEMEDIA_UPLOAD_TO

    if callable(upload_to):
        return upload_to(instance, filename)
    else:
        return upload_to


class MultiStorageFieldFile(ThumbnailerNameMixin,
                            easy_thumbnails_files.ThumbnailerFieldFile):
    def __init__(self, instance, field, name):
        """
        This is a little weird, but I couldn't find a better solution.
        Thumbnailer.__init__ is called first for proper object inizialization.
        Then we override some attributes defined at runtime with properties.
        We cannot simply call super().__init__ because filer Field objects
        doesn't have a storage attribute.
        """
        easy_thumbnails_files.Thumbnailer.__init__(self, None, name)
        self.instance = instance
        self.field = field
        self._committed = True
        self.storages = self.field.storages
        self.thumbnail_storages = self.field.thumbnail_storages
        self.storage = self._storage
        self.source_storage = self._source_storage
        self.thumbnail_storage = self._thumbnail_storage

    @property
    def _storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']

    @property
    def _source_storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']

    @property
    def _thumbnail_storage(self):
        if self.instance.is_public:
            return self.thumbnail_storages['public']
        else:
            return self.thumbnail_storages['private']


class MultiStorageFileField(easy_thumbnails_fields.ThumbnailerField):
    attr_class = MultiStorageFieldFile

    def __init__(self, verbose_name=None, name=None, upload_to_dict=None,
                 storages=None, thumbnail_storages=None, **kwargs):
        self.storages = storages or STORAGES
        self.thumbnail_storages = thumbnail_storages or THUMBNAIL_STORAGES
        super(easy_thumbnails_fields.ThumbnailerField, self).__init__(
                                      verbose_name=verbose_name, name=name,
                                      upload_to=generate_filename_multistorage,
                                      storage=None, **kwargs)
