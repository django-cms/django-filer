from easy_thumbnails import fields as easy_thumbnails_fields
from easy_thumbnails import files as easy_thumbnails_files
from django.core.files.storage import get_storage_class, default_storage
from django.core.files.base import File
from django.db.models.fields.files import ImageFieldFile, FieldFile
from django.db.models.fields.files import FileField, ImageField
from filer import settings as filer_settings

default_storages = {
    'public': filer_settings.FILER_PUBLICMEDIA_STORAGE,
    'private': filer_settings.FILER_PRIVATEMEDIA_STORAGE,
}

class MultiStorageFieldFile(easy_thumbnails_files.ThumbnailerFieldFile):#FieldFile):#
    def __init__(self, instance, field, name):
        # from FieldFile.__init__
        #super(FieldFile, self).__init__(None, name)
        File.__init__(self, None, name)
        self.instance = instance
        self.field = field
        #self.storage = field.storage
        self._committed = True
        
        # our special stuff
        self.storages = self.field.storages
        
        # from ThumbnailerFieldFiel.__init__
        #self.source_storage = self.field.storage
        self.source_storage = self.storage
#        thumbnail_storage = getattr(self.field, 'thumbnail_storage', None)
#        if thumbnail_storage:
#            self.thumbnail_storage = thumbnail_storage
    
    @property
    def storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']
    @property
    def thumbnail_storage(self):
        if self.instance.is_public:
            return self.storages['public']
        else:
            return self.storages['private']
    

class MultiStorageFileField(easy_thumbnails_fields.ThumbnailerField):#FileField):
    attr_class = MultiStorageFieldFile
    def __init__(self, verbose_name=None, name=None, upload_to='', storages=None, **kwargs):
        self.storages = storages or default_storages
        super(easy_thumbnails_fields.ThumbnailerField, self).__init__(verbose_name=verbose_name, name=name, upload_to=upload_to, storage=None, **kwargs)
        #super(MultiStorageFileField, self).__init__(verbose_name=verbose_name, name=name, upload_to=upload_to, storage=None, **kwargs)
        for key, value in self.storages.items():
            self.storages[key] = get_storage_class(value)()
    
    def get_directory_name(self):
        return super(MultiStorageFileField, self).get_directory_name()

    def get_filename(self, filename):
        return super(MultiStorageFileField, self).get_filename(filename)

    def generate_filename(self, instance, filename):
        return super(MultiStorageFileField, self).generate_filename(instance, filename)
