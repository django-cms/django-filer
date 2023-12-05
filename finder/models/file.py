import hashlib
import mimetypes
from functools import lru_cache, reduce
from operator import or_
from pathlib import Path

from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from filer import settings as filer_settings

from .inode import InodeManager, InodeModel


def mimetype_validator(value):
    if not mimetypes.guess_extension(value):
        msg = "'{mimetype}' is not a recognized MIME-Type."
        raise ValidationError(msg.format(mimetype=value))


class FileModelManager(InodeManager):
    def create_from_upload(self, uploaded_file, **kwargs):
        folder = kwargs.pop('folder')
        kwargs.update(
            parent=folder,
            name=uploaded_file.name,
            file_name=self.model.generate_filename(uploaded_file.name),
            mime_type=kwargs.pop('mime_type', uploaded_file.content_type),
            file_size=uploaded_file.size,
        )
        obj = self.model(**kwargs)
        (default_storage.base_location / obj.folder_path).mkdir(parents=True, exist_ok=True)
        sha1 = hashlib.sha1()
        with default_storage.open(obj.file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                sha1.update(chunk)
                destination.write(chunk)
        if default_storage.size(obj.file_path) != obj.file_size:
            raise IOError("File size mismatch between uploaded file and destination file")
        obj.sha1 = sha1.hexdigest()
        obj._for_write = True
        obj.save(force_insert=True)
        folder.refresh_from_db()
        return obj

    def get_model_for(self, mime_type):
        def lookup(mime_type):
            for model in InodeModel.file_models:
                if mime_type in model.accept_mime_types:
                    return model
            return None

        if model := lookup(mime_type):
            return model
        if model := lookup('/'.join((mime_type.split('/')[0], '*'))):
            return model
        return FileModel


class AbstractFileModel(InodeModel):
    data_fields = InodeModel.data_fields + ['file_size', 'file_name', 'sha1', 'mime_type']
    filer_public = Path(filer_settings.FILER_STORAGES['public']['main']['UPLOAD_TO_PREFIX'])

    file_name = models.CharField(
        _("File name"),
        max_length=255,
    )
    file_size = models.BigIntegerField(
        _("Size"),
    )
    sha1 = models.CharField(
        _("sha1"),
        max_length=40,
        blank=True,
        default='',
    )
    mime_type = models.CharField(
        max_length=255,
        help_text="MIME type of uploaded content",
        validators=[mimetype_validator],
        default='application/octet-stream',
    )

    class Meta:
        abstract = True
        verbose_name = _("File")
        verbose_name_plural = _("Files")
        default_permissions = []

    objects = FileModelManager()

    @property
    def folder(self):
        return self.parent

    @cached_property
    def folder_path(self):
        id = str(self.id)
        return self.filer_public / f'{id[0:2]}/{id[2:4]}/{id}'

    @property
    def file_path(self):
        return self.folder_path / self.file_name

    @cached_property
    def summary(self):
        return filesizeformat(self.file_size)

    @classmethod
    def generate_filename(cls, filename):
        return default_storage.generate_filename(filename).lower()

    @classmethod
    @lru_cache
    def mime_types_query(cls):
        queries = []
        for accept_mimetype in cls.accept_mime_types:
            if accept_mimetype == '*/*':
                queries.clear()
                break
            accept_mimetype_main, accept_mimetype_sub = accept_mimetype.split('/')
            if accept_mimetype_sub == '*':
                queries.append(models.Q(mime_type__startswith=f'{accept_mimetype_main}/'))
            else:
                queries.append(models.Q(mime_type=accept_mimetype))
        return reduce(or_, queries, models.Q())

    def get_download_url(self):
        """
        Hook to return the download url for a given file.
        """
        return default_storage.url(self.file_path)

    def get_thumbnail_url(self):
        """
        Hook to return the thumbnail url for a given file.
        """
        return staticfiles_storage.url('filer/icons/file-unknown.svg')

    @cached_property
    def mime_maintype(self):
        return self.mime_type.split('/')[0]

    @cached_property
    def mime_subtype(self):
        return self.mime_type.split('/')[1]

    def open(self, mode='rb'):
        return default_storage.open(self.file_path, mode)

    def copy_to(self, folder, **kwargs):
        """
        Copy the file to a destination folder and returns it.
        """
        model = self._meta.model
        kwargs.setdefault('name', self.name)
        kwargs.setdefault('owner', self.owner)
        kwargs.update(
            parent=folder,
            file_size=self.file_size,
            sha1=self.sha1,
            mime_type=self.mime_type,
            file_name=self.file_name,
            meta_data=self.meta_data,
        )
        obj = model(**kwargs)
        (default_storage.base_location / obj.folder_path).mkdir(parents=True, exist_ok=True)
        with default_storage.open(self.file_path, 'rb') as readhandle:
            default_storage.save(obj.file_path, readhandle)
        obj._for_write = True
        obj.save(force_insert=True)
        folder.refresh_from_db()
        return obj

    def delete(self, using=None, keep_parents=False):
        if not self._meta.abstract and default_storage.exists(self.file_path):
            default_storage.delete(self.file_path)
        super().delete(using, keep_parents)


class FileModel(AbstractFileModel):
    """
    Fallback model for all files that do not match any other model.
    """
    accept_mime_types = ['*/*']
