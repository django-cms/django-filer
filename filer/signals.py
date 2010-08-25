from filer.models.filer_file_storage import (PublicFileSystemStorage,
                                             PrivateFileSystemStorage)

def set_file_field_storage(sender, instance, **kwargs):
    if instance.is_public:
        instance._file.storage = PublicFileSystemStorage()
    else:
        instance._file.storage = PrivateFileSystemStorage()