import os.path

from filer.models import BaseImage
from filer.models.filemodels import File


class Video(File):
    _icon = "video"

    class Meta:
        app_label = 'extended_app'
        default_manager_name = 'objects'

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        filename_extensions = ['.dv', '.mov', '.mp4', '.avi', '.wmv', ]
        ext = os.path.splitext(iname)[1].lower()
        return ext in filename_extensions


class ExtImage(BaseImage):
    _icon = "image"

    class Meta:
        app_label = 'extended_app'
        default_manager_name = 'objects'
