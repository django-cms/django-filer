# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import hashlib
import os
from datetime import datetime

from django.conf import settings
from django.core import urlresolvers
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from . import mixins
from .. import settings as filer_settings
from ..fields.multistorage_file import MultiStorageFileField
from ..utils.compatibility import LTE_DJANGO_1_7, python_2_unicode_compatible
from .foldermodels import Folder

try:
    from polymorphic.models import PolymorphicModel
    from polymorphic.managers import PolymorphicManager
except ImportError:
    # django-polymorphic < 0.8
    from polymorphic import PolymorphicModel, PolymorphicManager


class FileManager(PolymorphicManager):
    def find_all_duplicates(self):
        r = {}
        for file_obj in self.all():
            if file_obj.sha1:
                q = self.filter(sha1=file_obj.sha1)
                if len(q) > 1:
                    r[file_obj.sha1] = q
        return r

    def find_duplicates(self, file_obj):
        return [i for i in self.exclude(pk=file_obj.pk).filter(sha1=file_obj.sha1)]


@python_2_unicode_compatible
class File(PolymorphicModel, mixins.IconsMixin):
    file_type = 'File'
    _icon = "file"
    _file_data_changed_hint = None

    folder = models.ForeignKey(Folder, verbose_name=_('folder'), related_name='all_files',
        null=True, blank=True)
    file = MultiStorageFileField(_('file'), null=True, blank=True, max_length=255)
    _file_size = models.IntegerField(_('file size'), null=True, blank=True)

    sha1 = models.CharField(_('sha1'), max_length=40, blank=True, default='')

    has_all_mandatory_data = models.BooleanField(_('has all mandatory data'), default=False, editable=False)

    original_filename = models.CharField(_('original filename'), max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, default="", blank=True,
        verbose_name=_('name'))
    description = models.TextField(null=True, blank=True,
        verbose_name=_('description'))

    owner = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        related_name='owned_%(class)ss', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_('owner'))

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

    is_public = models.BooleanField(
        default=filer_settings.FILER_IS_PUBLIC_DEFAULT,
        verbose_name=_('Permissions disabled'),
        help_text=_('Disable any permission checking for this '
                    'file. File will be publicly accessible '
                    'to anyone.'))

    objects = FileManager()

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        return True  # I match all files...

    def __init__(self, *args, **kwargs):
        super(File, self).__init__(*args, **kwargs)
        self._old_is_public = self.is_public
        self.file_data_changed(post_init=True)

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
        except:
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
        src_file.open()
        # hint file_data_changed callback that data is actually unchanged
        self._file_data_changed_hint = False
        self.file = dst_storage.save(dst_file_name,
            ContentFile(src_file.read()))
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

    def generate_sha1(self):
        sha = hashlib.sha1()
        self.file.seek(0)
        while True:
            buf = self.file.read(104857600)
            if not buf:
                break
            sha.update(buf)
        self.sha1 = sha.hexdigest()
        # to make sure later operations can read the whole file
        self.file.seek(0)

    def save(self, *args, **kwargs):
        # check if this is a subclass of "File" or not and set
        # _file_type_plugin_name
        if self.__class__ == File:
            # what should we do now?
            # maybe this has a subclass, but is being saved as a File instance
            # anyway. do we need to go check all possible subclasses?
            pass
        elif issubclass(self.__class__, File):
            self._file_type_plugin_name = self.__class__.__name__
        if self._old_is_public != self.is_public and self.pk:
            self._move_file()
            self._old_is_public = self.is_public
        super(File, self).save(*args, **kwargs)
    save.alters_data = True

    def delete(self, *args, **kwargs):
        # Delete the model before the file
        super(File, self).delete(*args, **kwargs)
        # Delete the file if there are no other Files referencing it.
        if not File.objects.filter(file=self.file.name, is_public=self.is_public).exists():
            self.file.delete(False)
    delete.alters_data = True

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
        if not user.is_authenticated():
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        elif self.folder:
            return self.folder.has_generic_permission(request, permission_type)
        else:
            return False

    def __str__(self):
        if self.name in ('', None):
            text = "%s" % (self.original_filename,)
        else:
            text = "%s" % (self.name,)
        return text

    def get_admin_change_url(self):
        if LTE_DJANGO_1_7:
            model_name = self._meta.module_name
        else:
            model_name = self._meta.model_name
        return urlresolvers.reverse(
            'admin:{0}_{1}_change'.format(self._meta.app_label, model_name),
            args=(self.pk,)
        )

    def get_admin_delete_url(self):
        try:
            # Django <=1.6
            model_name = self._meta.module_name
        except AttributeError:
            # Django >1.6
            model_name = self._meta.model_name
        return urlresolvers.reverse(
            'admin:{0}_{1}_delete'.format(self._meta.app_label, model_name,),
            args=(self.pk,))

    @property
    def url(self):
        """
        to make the model behave like a file field
        """
        try:
            r = self.file.url
        except:
            r = ''
        return r

    @property
    def canonical_time(self):
        if settings.USE_TZ:
            return int((self.uploaded_at - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds())
        else:
            return int((self.uploaded_at - datetime(1970, 1, 1)).total_seconds())

    @property
    def canonical_url(self):
        url = ''
        if self.file and self.is_public:
            try:
                url = urlresolvers.reverse('canonical', kwargs={
                    'uploaded_at': self.canonical_time,
                    'file_id': self.id
                })
            except urlresolvers.NoReverseMatch:
                pass  # No canonical url, return empty string
        return url

    @property
    def path(self):
        try:
            return self.file.path
        except:
            return ""

    @property
    def size(self):
        return self._file_size or 0

    @property
    def extension(self):
        filetype = os.path.splitext(self.file.name)[1].lower()
        if len(filetype) > 0:
            filetype = filetype[1:]
        return filetype

    @property
    def logical_folder(self):
        """
        if this file is not in a specific folder return the Special "unfiled"
        Folder object
        """
        if not self.folder:
            from .virtualitems import UnsortedImages
            return UnsortedImages()
        else:
            return self.folder

    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        folder_path = []
        if self.folder:
            folder_path.extend(self.folder.get_ancestors())
        folder_path.append(self.logical_folder)
        return folder_path

    @property
    def duplicates(self):
        return File.objects.find_duplicates(self)

    class Meta(object):
        app_label = 'filer'
        verbose_name = _('file')
        verbose_name_plural = _('files')
