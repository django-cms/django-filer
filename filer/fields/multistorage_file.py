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
        path, source_filename = os.path.split(self.name)
        filename, extension = os.path.splitext(source_filename)
        if format_ext.starts_with('.'):
            newfilename = '%s%s' % (filename, format_ext)
        else:
            newfilename = '%s.%s' % (filename, format_ext)
        return os.path.join(path, newfilename)

    def get_format_url(self, ext):
        base_name = self.get_format_name(format_ext)
        if self.format_storage.exists(base_name):
            return os.path.join(self.format_storage.base_url, base_name)
        else:
            raise NameError


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
        self.formats_storage = self.field.format_storages

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
            return self.formats_storages['public']
        else:
            return self.formats_storages['private']

    def get_format(self, options, save=True):
        #wtf is opaque vs transparent???
        pass
        

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

    # make versions devia estar aki!!!!
