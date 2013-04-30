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
            dir_parents_of_entry = entry.filename.split('/')[:-1]
            filename = os.path.basename(entry.filename)
            parent_dir = self.folder
            for directory_name in dir_parents_of_entry:
                parent_dir = self._create_folder(directory_name, parent_dir)
            if filename:
                data = zippy.read(entry)
                self._create_file(filename, parent_dir, data)

    def _create_folder(self, name, parent):
        current_dir, _ = Folder.objects.get_or_create(
            name=name,
            parent=parent,
            owner=self.owner,
        )
        return current_dir

    def _create_file(self, basename, folder, data):
        file_data = ContentFile(data)
        file_data.name = basename
        file_object = File.objects.create(
            original_filename=basename,
            folder=folder,
            owner=self.owner,
            file=file_data,
        )
        file_data.close()


    class Meta:
        app_label = 'filer'
        verbose_name = _('archive')
        verbose_name_plural = _('archives')
