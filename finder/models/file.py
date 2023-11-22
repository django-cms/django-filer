import hashlib
import mimetypes
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
    accept_mime_types = ['*/*']
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
    def file_data_changed(self, post_init=False):
        """
        This is called whenever self.file changes (including initial set in __init__).
        MultiStorageFileField has a custom descriptor which calls this function when
        field value is changed.
        Returns True if data related attributes were updated, False otherwise.
        """
        if self._file_data_changed_hint is not None:
            data_changed_hint = self._file_data_changed_hint
            self._file_data_changed_hint = None
            if not data_changed_hint:
                return False
        if post_init and self._file_size and self.sha1:
            # When called from __init__, only update if values are empty.
            # This makes sure that nothing is done when instantiated from db.
            return False
        # cache the file size
        try:
            self._file_size = self.file.size
        except:   # noqa
            self._file_size = None
        # generate SHA1 hash
        try:
            self.generate_sha1()
        except Exception:
            self.sha1 = ''
        return True

    def _move_file(self):
        """
        Move the file from src to dst.
        """
        src_file_name = self.file.name
        dst_file_name = self._meta.get_field('file').generate_filename(
            self, self.original_filename)

        if self.is_public:
            src_storage = self.file.storages['private']
            dst_storage = self.file.storages['public']
        else:
            src_storage = self.file.storages['public']
            dst_storage = self.file.storages['private']

        # delete the thumbnail
        # We are toggling the is_public to make sure that easy_thumbnails can
        # delete the thumbnails
        self.is_public = not self.is_public
        self.file.delete_thumbnails()
        self.is_public = not self.is_public
        # This is needed because most of the remote File Storage backend do not
        # open the file.
        src_file = src_storage.open(src_file_name)
        # Context manager closes file after reading contents
        with src_file.open() as f:
            content_file = ContentFile(f.read())
        # hint file_data_changed callback that data is actually unchanged
        self._file_data_changed_hint = False
        self.file = dst_storage.save(dst_file_name, content_file)
        src_storage.delete(src_file_name)

    def _copy_file(self, destination, overwrite=False):
        """
        Copies the file to a destination files and returns it.
        """

        if overwrite:
            # If the destination file already exists default storage backend
            # does not overwrite it but generates another filename.
            # TODO: Find a way to override this behavior.
            raise NotImplementedError

        src_file_name = self.file.name
        storage = self.file.storages['public' if self.is_public else 'private']

        # This is needed because most of the remote File Storage backend do not
        # open the file.
        src_file = storage.open(src_file_name)
        src_file.open()
        return storage.save(destination, ContentFile(src_file.read()))

    @property
    def label(self):
        if self.name in ['', None]:
            text = self.original_filename or 'unnamed file'
        else:
            text = self.name
        text = "%s" % (text,)
        return text

    def __lt__(self, other):
        return self.label.lower() < other.label.lower()

    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')

    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')

    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')

    def has_generic_permission(self, request, permission_type):
        """
        Return true if the current user has permission on this
        image. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated:
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        elif self.folder:
            return self.folder.has_generic_permission(request, permission_type)
        else:
            return False
