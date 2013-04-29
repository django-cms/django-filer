from filer.models.filemodels import File, Folder
from filer import settings as filer_settings
from django.utils.translation import ugettext_lazy as _
from django.core.files.base import ContentFile
import os.path
import zipfile
import StringIO

class Archive(File):
    file_type = 'Archive'
    _icon = 'archive'
    _filename_extensions = ['.zip', '.tar', '.gz', '.bz2']

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        extension = os.path.splitext(iname)[-1].lower()
        return extension in Archive._filename_extensions

    def extract(self):
        self.file.seek(0)
        data = self.file.read() # XXX this blows if the archive is huge.
        dummy_file = StringIO.StringIO(data)
        self.extract_zip(dummy_file)

    def extract_zip(self, file_info):
        zippy = zipfile.ZipFile(file_info)
        entries = zippy.infolist()
        for entry in entries:
            fields = entry.filename.split('/')
            dir_parents_of_entry = fields[:-1]
            filename = fields[-1]
            parent_dir = self.folder
            for directory_name in dir_parents_of_entry:
                current_dir, _ = Folder.objects.get_or_create(
                    name=directory_name,
                    parent=parent_dir,
                    owner=self.owner,
                )
                parent_dir = current_dir
            if filename is not '':
                zippy_file = zippy.open(entry.filename)
                data = zippy_file.read()
                zippy_file.close()
                file_data = ContentFile(data)
                file_data.name = filename
                file_object, _ = File.objects.get_or_create(
                    original_filename=filename,
                    folder=parent_dir,
                    owner=self.owner,
                    file=file_data,
                )
                file_object.save()
                file_data.close()
        zippy.close()


    class Meta:
        app_label = 'filer'
        verbose_name = _('archive')
        verbose_name_plural = _('archives')
