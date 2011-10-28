#-*- coding: utf-8 -*-
import os
from django.core.files.base import File
from django.core.files.storage import Storage
from django.db.models.fields.files import FieldFile
from easy_thumbnails import fields as easy_thumbnails_fields, \
    files as easy_thumbnails_files
from filer import settings as filer_settings
from filer.utils.filer_easy_thumbnails import ThumbnailerNameMixin
from filer.utils.video import get_format_name as get_video_name

STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_STORAGE,
}
THUMBNAIL_STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_THUMBNAIL_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_THUMBNAIL_STORAGE,
}
FORMAT_STORAGES = {
    'public': filer_settings.FILER_PUBLICMEDIA_FORMATS_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_FORMATS_STORAGE,
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


class FormatNameMixin(object):
    def get_format_name(self, ext):
        return get_video_name(self.name, ext)

    def get_format_url(self, ext):
        base_name = self.get_format_name(ext)
        if self.format_storage.exists(base_name):
            return self.format_storage.url(base_name)
        else:
            raise NameError

    def get_poster_url(self):
        return self.get_format_url('png')


class FormatFieldFile(FieldFile):
    """Used when serving formats through serve_protected_format"""
    def __init__(self, instance, field, name, storage):
        super(FormatFieldFile, self).__init__(instance, field, name)
        self.storage = storage


class MultiStorageFieldFile(ThumbnailerNameMixin,
                            easy_thumbnails_files.ThumbnailerFieldFile,
                            FormatNameMixin):
    def __init__(self, instance, field, name):
        File.__init__(self, None, name)
        self.instance = instance
        self.field = field
        self._committed = True
        self.storages = self.field.storages
        self.thumbnail_storages = self.field.thumbnail_storages
        self.format_storages = self.field.format_storages

    @property
    def storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']

    @property
    def source_storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']

    @property
    def thumbnail_storage(self):
        if self.instance.is_public:
            return self.thumbnail_storages['public']
        else:
            return self.thumbnail_storages['private']

    @property
    def format_storage(self):
        if self.instance.is_public:
            return self.format_storages['public']
        else:
            return self.format_storages['private']


class MultiStorageFileField(easy_thumbnails_fields.ThumbnailerField):
    attr_class = MultiStorageFieldFile

    def __init__(self, verbose_name=None, name=None, upload_to_dict=None,
                 storages=None, thumbnail_storages=None, format_storages=None,
                 **kwargs):
        self.storages = storages or STORAGES
        self.thumbnail_storages = thumbnail_storages or THUMBNAIL_STORAGES
        self.format_storages = format_storages or FORMAT_STORAGES
        super(easy_thumbnails_fields.ThumbnailerField, self).__init__(
                                      verbose_name=verbose_name, name=name,
                                      upload_to=generate_filename_multistorage,
                                      storage=None, **kwargs)
