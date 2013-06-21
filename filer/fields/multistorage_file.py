#-*- coding: utf-8 -*-
from easy_thumbnails import fields as easy_thumbnails_fields, \
    files as easy_thumbnails_files

from filer import settings as filer_settings
from filer.utils.filer_easy_thumbnails import ThumbnailerNameMixin
from filer.utils.cdn import get_file_url_from_cdn


STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_STORAGE,
}
THUMBNAIL_STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_THUMBNAIL_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE,
}
THUMBNAIL_OPTIONS = {
    'public': filer_settings.FILER_PUBLICMEDIA_THUMBNAIL_OPTIONS,
    'private': filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_OPTIONS,
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


class CdnAwareThumbnailFile(easy_thumbnails_files.ThumbnailFile):

    def __init__(self, thumbnail_file, filer_file):
        self._thumbnail_file = thumbnail_file
        self._filer_file = filer_file

    def __getattr__(self, attr_name):
        return getattr(self._thumbnail_file, attr_name)

    def _get_url(self):
        url = super(CdnAwareThumbnailFile, self).url
        return get_file_url_from_cdn(self._filer_file, url)
    url = property(_get_url)


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
        self.thumbnail_options = self.field.thumbnail_options
        self.storage = self._storage
        self.source_storage = self._source_storage
        self.thumbnail_storage = self._thumbnail_storage
        self.thumbnail_basedir = self._thumbnail_base_dir

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

    @property
    def _thumbnail_base_dir(self):
        if self.instance.is_public:
            return self.thumbnail_options['public'].get('base_dir', '')
        else:
            return self.thumbnail_options['private'].get('base_dir', '')

    def _get_url(self):
        url = super(MultiStorageFieldFile, self)._get_url()
        return get_file_url_from_cdn(self.instance, url)
    url = property(_get_url)

    def save(self, name, content, save=True):
        content.seek(0) # Ensure we upload the whole file
        super(MultiStorageFieldFile, self).save(name, content, save)

    def get_thumbnail(self, opts, save=True, generate=None):
        thumbnail = super(MultiStorageFieldFile, self).get_thumbnail(opts, save, generate)
        return CdnAwareThumbnailFile(thumbnail, self.instance)


class MultiStorageFileField(easy_thumbnails_fields.ThumbnailerField):
    attr_class = MultiStorageFieldFile

    def __init__(self, verbose_name=None, name=None,
                 storages=None, thumbnail_storages=None, thumbnail_options=None, **kwargs):
        self.storages = storages or STORAGES
        self.thumbnail_storages = thumbnail_storages or THUMBNAIL_STORAGES
        self.thumbnail_options = thumbnail_options or THUMBNAIL_OPTIONS
        super(easy_thumbnails_fields.ThumbnailerField, self).__init__(
                                      verbose_name=verbose_name, name=name,
                                      upload_to=generate_filename_multistorage,
                                      storage=None, **kwargs)
