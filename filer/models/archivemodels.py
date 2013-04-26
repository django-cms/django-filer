from filer.models.filemodels import File
from filer import settings as filer_settings
from django.utils.translation import ugettext_lazy as _
import os.path

class Archive(File):
    file_type = 'Archive'
    _icon = 'archive'
    _filename_extensions = ['.zip', '.tar', '.gz', '.bz2']

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        extension = os.path.splitext(iname)[-1].lower()
        return extension in Archive._filename_extensions

    class Meta:
        app_label = 'filer'    
        verbose_name = _('archive')
        verbose_name_plural = _('archives')
